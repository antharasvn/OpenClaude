"""Telegram message/media handlers + batching + streaming UI."""

import asyncio
import html
import re
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import (
    ADMIN_USER_ID, ALL_TOOLS, BATCH_WINDOW, STATUS_EDIT_INTERVAL,
    TELEGRAM_MAX_LENGTH, is_authorized,
    get_thread_id,
)
from bot.logging_setup import logger, get_workspace_logger
from bot.sessions import session_key, get_session_id, load_sessions, clear_session, set_usage, get_context_pct
from bot.workspaces import ensure_workspace, get_working_dir
from bot.renderer import TelegramRenderer, split_message
from bot.claude import stream_claude, finished_line, format_tool_status, kill_active_proc
from bot.sdk_session import sdk_sessions, SDKSession

# Image URL detection patterns
_IMAGE_EXTENSIONS = re.compile(r'\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s)]*)?$', re.IGNORECASE)
_MD_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_BARE_URL_RE = re.compile(r'(?<!\()(https?://\S+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s)]*)?)(?!\))', re.IGNORECASE)


def _extract_image_urls(text: str) -> tuple[str, list[str]]:
    """Extract image URLs from markdown and return (cleaned_text, urls)."""
    urls: list[str] = []

    # Extract markdown images: ![alt](url)
    for match in _MD_IMAGE_RE.finditer(text):
        url = match.group(2)
        if _IMAGE_EXTENSIONS.search(url):
            urls.append(url)

    # Remove markdown image syntax for extracted images
    cleaned = _MD_IMAGE_RE.sub(
        lambda m: '' if _IMAGE_EXTENSIONS.search(m.group(2)) else m.group(0),
        text,
    )

    # Extract bare image URLs (not already captured in markdown syntax)
    for match in _BARE_URL_RE.finditer(cleaned):
        url = match.group(1)
        if url not in urls:
            urls.append(url)

    # Remove bare image URLs from text
    if urls:
        cleaned = _BARE_URL_RE.sub(
            lambda m: '' if m.group(1) in urls else m.group(0),
            cleaned,
        )

    # Clean up leftover blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()

    return cleaned, urls


# Populated at startup via post_init callback
BOT_USERNAME: str = ""

renderer = TelegramRenderer()

TYPING_INTERVAL = 4  # seconds between typing indicator refreshes (Telegram expires at ~5s)


async def _typing_loop(bot, chat_id: int) -> None:
    """Send 'typing' chat action periodically until cancelled."""
    try:
        while True:
            try:
                await bot.send_chat_action(chat_id=chat_id, action="typing")
            except Exception:
                logger.debug("typing indicator send failed for chat %d", chat_id)
            await asyncio.sleep(TYPING_INTERVAL)
    except asyncio.CancelledError:
        pass


# Per-user locks to prevent concurrent Claude calls for the same user
_user_locks: dict[int, asyncio.Lock] = {}

# Per-session stop events for /stop command
_stop_events: dict[str, asyncio.Event] = {}

# Per-session streaming task references for /stop cancellation
_streaming_tasks: dict[str, asyncio.Task] = {}


def _get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


# ---------------------------------------------------------------------------
# Group / Topic Helpers
# ---------------------------------------------------------------------------

def should_respond(update: Update) -> bool:
    """Decide whether the bot should respond to this message."""
    chat = update.effective_chat
    if chat.type == "private":
        return True

    msg = update.message
    if not msg:
        return False

    thread_id = get_thread_id(update)
    from commands.config import get_respond_mode
    mode = get_respond_mode(chat.id, thread_id)

    if mode == "all":
        return True

    if msg.entities:
        for entity in msg.entities:
            if entity.type == "mention":
                mention = msg.text[entity.offset:entity.offset + entity.length]
                if mention.lower() == f"@{BOT_USERNAME.lower()}":
                    return True

    if msg.reply_to_message and msg.reply_to_message.from_user:
        if msg.reply_to_message.from_user.username and \
           msg.reply_to_message.from_user.username.lower() == BOT_USERNAME.lower():
            return True

    return False


def strip_bot_mention(text: str) -> str:
    """Remove @bot_username from message text."""
    if BOT_USERNAME:
        text = re.sub(rf"@{re.escape(BOT_USERNAME)}\b", "", text, flags=re.IGNORECASE).strip()
    return text


def get_reply_prefix(update: Update) -> str:
    """If the user is replying to a message, return a prefix with the quoted text."""
    reply = update.message.reply_to_message if update.message else None
    if not reply:
        return ""

    # Determine who sent the replied-to message
    from_user = reply.from_user
    if from_user:
        if BOT_USERNAME and from_user.username and from_user.username.lower() == BOT_USERNAME.lower():
            sender = "you (the assistant)"
        else:
            sender = from_user.first_name or from_user.username or str(from_user.id)
    else:
        sender = "unknown"

    quoted = reply.text or reply.caption or ""
    if not quoted:
        return f'[User is replying to a message from {sender} (no text content)]\n'

    if len(quoted) > 500:
        quoted = quoted[:500] + "…"

    # Sanitize to reduce prompt injection risk from quoted text
    quoted = quoted.replace("[", "(").replace("]", ")")
    return f'[User is replying to this message from {sender}:\n"{quoted}"]\n'


# ---------------------------------------------------------------------------
# Message Sending
# ---------------------------------------------------------------------------

async def send_rendered(
    update: Update,
    text: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Render markdown to HTML and send, splitting if needed."""
    md_chunks = split_message(text)
    thread_id = get_thread_id(update)

    for md_chunk in md_chunks:
        chunk = renderer.render(md_chunk)
        try:
            await update.message.reply_text(
                chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                message_thread_id=thread_id or None,
            )
        except Exception:
            logger.warning("HTML send failed for chunk, falling back to plain text")
            plain = re.sub(r"<[^>]+>", "", chunk)
            plain_chunks = split_message(plain)
            for pc in plain_chunks:
                try:
                    await update.message.reply_text(
                        pc,
                        message_thread_id=thread_id or None,
                    )
                except Exception:
                    logger.warning("Plain text fallback also failed")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    from commands import ALL_COMMANDS

    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text(
            f"Unauthorized. Your user ID is: {user.id}\n"
            "Add it to ALLOWED_USERS in .env to use this bot."
        )
        return

    cmd_lines = [
        "/new \u2014 Start a new conversation",
        "/stop \u2014 Stop current generation",
        "/status \u2014 Show session info",
    ]
    for name, desc in ALL_COMMANDS:
        cmd_lines.append(f"/{name} \u2014 {desc}")

    await update.message.reply_text(
        "OpenClaude is online.\n"
        "Send me a message and I'll route it to Claude.\n\n"
        "Commands:\n" + "\n".join(cmd_lines)
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new command — clear session and start fresh."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    session_uid = user.id if update.effective_chat.type == "private" else 0
    skey = session_key(chat_id, thread_id, session_uid)

    # Stop any active generation first (same full cleanup as /stop)
    if _stop_events.get(skey):
        await _force_stop_session(skey, chat_id, thread_id, session_uid)

    clear_session(chat_id, thread_id, session_uid)
    await update.message.reply_text(
        "Session cleared. Starting fresh.",
        message_thread_id=thread_id or None,
    )
    logger.info("Session cleared for user %d in chat %d thread %d", user.id, chat_id, thread_id)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command — show user ID and session info."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text(f"Your Telegram user ID: {user.id}")
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    session_uid = user.id if update.effective_chat.type == "private" else 0
    sid = get_session_id(chat_id, thread_id, session_uid)
    sessions = load_sessions()
    key = session_key(chat_id, thread_id, session_uid)
    user_data = sessions.get(key, {})

    status_lines = [
        f"<b>OpenClaude Status</b>",
        f"",
        f"<b>User ID:</b> <code>{user.id}</code>",
        f"<b>Username:</b> @{html.escape(user.username) if user.username else 'N/A'}",
        f"<b>Session:</b> <code>{sid or 'None'}</code>",
    ]

    if updated := user_data.get("updated_at"):
        status_lines.append(f"<b>Last active:</b> {updated}")

    chat_dir = get_working_dir(chat_id)
    status_lines.extend([
        f"",
        f"<b>Working dir:</b> <code>{chat_dir}</code>",
        f"<b>Allowed tools:</b> {ALL_TOOLS}",
    ])

    await update.message.reply_text(
        "\n".join(status_lines),
        parse_mode=ParseMode.HTML,
        message_thread_id=thread_id or None,
    )


async def _force_stop_session(skey: str, chat_id: int, thread_id: int, session_uid: int) -> None:
    """Kill subprocess, cancel streaming task, and force-cleanup lock/streams.

    Shared by /stop and /new to ensure full cleanup.
    """
    from bot.streams import remove_active_stream

    stop_event = _stop_events.get(skey)
    if stop_event:
        stop_event.set()

    # Hard-kill the subprocess tree
    sdk_session = sdk_sessions.get(skey)
    if sdk_session:
        sdk_session.hard_kill()
        if sdk_session.connected:
            await sdk_session.disconnect()
        sdk_sessions.pop(skey, None)

    kill_active_proc(skey)

    # Cancel the streaming asyncio task so finally blocks run
    task = _streaming_tasks.get(skey)
    if task and not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            pass

    # Force cleanup in case the task didn't finish or clean up properly
    _streaming_tasks.pop(skey, None)
    _stop_events.pop(skey, None)
    remove_active_stream(chat_id, thread_id, session_uid)
    lock = _user_locks.get(session_uid)
    if lock and lock.locked():
        try:
            lock.release()
        except RuntimeError:
            pass


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stop command — cancel current Claude generation."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    session_uid = user.id if update.effective_chat.type == "private" else 0
    skey = session_key(chat_id, thread_id, session_uid)
    tg_thread_id = thread_id or None

    stop_event = _stop_events.get(skey)
    if not stop_event:
        await update.message.reply_text(
            "Nothing to stop.",
            message_thread_id=tg_thread_id,
        )
        return

    await _force_stop_session(skey, chat_id, thread_id, session_uid)

    await update.message.reply_text(
        "Generation stopped.",
        message_thread_id=tg_thread_id,
    )
    logger.info("User %d stopped generation in chat %d thread %d", user.id, chat_id, thread_id)


# ---------------------------------------------------------------------------
# Message Batching
# ---------------------------------------------------------------------------

_batch_buffers: dict[str, list[str]] = {}
_batch_timers: dict[str, asyncio.TimerHandle] = {}
_batch_updates: dict[str, tuple[Update, ContextTypes.DEFAULT_TYPE]] = {}
_batch_meta: dict[str, tuple[int, int, int]] = {}


async def queue_message(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        chat_id: int, thread_id: int, user_id: int,
                        claude_message: str) -> None:
    """Add a message to the batch buffer. After BATCH_WINDOW seconds of quiet, flush all."""
    session_user_id = user_id if update.effective_chat.type == "private" else 0
    key = session_key(chat_id, thread_id, session_user_id)

    _batch_buffers.setdefault(key, []).append(claude_message)
    _batch_updates[key] = (update, context)
    _batch_meta[key] = (chat_id, thread_id, user_id)

    if key in _batch_timers:
        _batch_timers[key].cancel()

    loop = asyncio.get_event_loop()
    _batch_timers[key] = loop.call_later(
        BATCH_WINDOW,
        lambda k=key: asyncio.ensure_future(_flush_batch(k)),
    )


async def _flush_batch(key: str) -> None:
    """Flush the batch buffer — combine messages and send to Claude."""
    messages = _batch_buffers.pop(key, [])
    update_ctx = _batch_updates.pop(key, None)
    meta = _batch_meta.pop(key, None)
    _batch_timers.pop(key, None)

    if not messages or not update_ctx or not meta:
        return

    update, context = update_ctx
    chat_id, thread_id, user_id = meta

    if len(messages) == 1:
        combined = messages[0]
    else:
        combined = "\n\n".join(messages)

    await run_with_streaming(update, context, chat_id, thread_id, user_id, combined)


# ---------------------------------------------------------------------------
# Streaming UI
# ---------------------------------------------------------------------------

async def run_with_streaming(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             chat_id: int, thread_id: int, user_id: int,
                             claude_message: str, _is_compact: bool = False) -> None:
    """Stream Claude output, show tool progress, then send final response."""
    session_user_id = user_id if update.effective_chat.type == "private" else 0
    tg_thread_id = thread_id or None
    from commands.config import get_streaming, get_verbose
    streaming = get_streaming(chat_id, thread_id)
    show_tools = get_verbose(chat_id, thread_id)
    status_msg = None
    finished_lines: list[str] = []
    current_active: str = ""
    last_edit_time: float = 0

    live_msg = None
    live_text = ""
    flushed_text = ""  # text already rendered into a finalized message
    last_live_edit: float = 0
    LIVE_EDIT_INTERVAL = 1.0

    async def _update_status(new_active: str = "") -> None:
        nonlocal status_msg, current_active, last_edit_time
        current_active = new_active
        lines = list(finished_lines)
        if current_active:
            lines.append(current_active)
        if not lines:
            return

        text = "\n".join(lines)

        now = asyncio.get_event_loop().time()
        if status_msg and (now - last_edit_time) < STATUS_EDIT_INTERVAL:
            return

        try:
            if status_msg is None:
                status_msg = await update.message.reply_text(
                    text,
                    message_thread_id=tg_thread_id,
                )
            else:
                await status_msg.edit_text(text)
            last_edit_time = asyncio.get_event_loop().time()
        except Exception:
            pass

    async def _update_live(text: str) -> None:
        nonlocal live_msg, last_live_edit

        now = asyncio.get_event_loop().time()
        if live_msg and (now - last_live_edit) < LIVE_EDIT_INTERVAL:
            return

        display = text[:TELEGRAM_MAX_LENGTH - 20] + " \u270d\ufe0f" if text else ""
        if not display:
            return

        try:
            if live_msg is None:
                live_msg = await update.message.reply_text(
                    display,
                    message_thread_id=tg_thread_id,
                )
            else:
                await live_msg.edit_text(display)
            last_live_edit = asyncio.get_event_loop().time()
        except Exception:
            pass

    response_text = None
    stopped = False
    chat_working_dir = get_working_dir(chat_id)
    skey = session_key(chat_id, thread_id, session_user_id)

    typing_task = None

    try:
        await asyncio.wait_for(_get_user_lock(session_user_id).acquire(), timeout=300)
    except asyncio.TimeoutError:
        logger.error("Lock acquisition timed out for user %d in chat %d", session_user_id, chat_id)
        try:
            await update.message.reply_text(
                "Still processing a previous request. Use /stop to cancel it.",
                message_thread_id=tg_thread_id,
            )
        except Exception:
            pass
        return

    try:
        # Only register task/stop_event for primary calls — auto-compact is nested
        # and must not clobber the outer call's registration.
        if not _is_compact:
            _streaming_tasks[skey] = asyncio.current_task()
        stop_event = asyncio.Event()
        if not _is_compact:
            _stop_events[skey] = stop_event

        # Start typing indicator — runs until cancelled
        typing_task = asyncio.create_task(_typing_loop(context.bot, chat_id))
        try:
            async for event in stream_claude(claude_message, chat_id, thread_id, session_user_id,
                                             working_dir=chat_working_dir, verbose=streaming,
                                             stop_event=stop_event,
                                             real_user_id=user_id):
                etype = event.get("type")

                if etype == "text_block":
                    # Completed text block (before tool use) — flush live in place
                    if live_msg and live_text:
                        try:
                            rendered = renderer.render(event["text"])
                            await live_msg.edit_text(
                                rendered[:TELEGRAM_MAX_LENGTH],
                                parse_mode=ParseMode.HTML,
                                disable_web_page_preview=True,
                            )
                        except Exception:
                            pass
                        flushed_text = event["text"]
                        live_msg = None
                        live_text = ""

                elif etype == "tool_use":
                    # Flush any remaining live text before showing tool status
                    if live_msg and live_text:
                        try:
                            rendered = renderer.render(live_text)
                            await live_msg.edit_text(
                                rendered[:TELEGRAM_MAX_LENGTH],
                                parse_mode=ParseMode.HTML,
                                disable_web_page_preview=True,
                            )
                        except Exception:
                            pass
                        flushed_text = live_text
                        live_msg = None
                        live_text = ""
                    if show_tools:
                        if current_active:
                            finished_lines.append(finished_line(current_active))
                        await _update_status(event["status"])

                elif etype == "tool_result":
                    if show_tools:
                        if current_active:
                            finished_lines.append(finished_line(current_active))
                            await _update_status("")

                elif etype == "partial":
                    live_text += event["text"]
                    # Stop typing once visible output is streaming
                    if typing_task and not typing_task.done():
                        typing_task.cancel()
                    await _update_live(live_text)

                elif etype == "result":
                    response_text = event.get("text", "")
                    usage_data = {k: event.get(k) for k in ("usage", "cost", "num_turns", "duration_ms", "duration_api_ms") if event.get(k) is not None}
                    if usage_data:
                        set_usage(chat_id, thread_id, session_user_id, usage_data)

                elif etype == "error":
                    response_text = event.get("text", "An error occurred.")

                elif etype == "silent":
                    response_text = ""

                elif etype == "stopped":
                    stopped = True

            # Final flush of any buffered live text
            if live_text:
                await _update_live(live_text)
        finally:
            if not _is_compact:
                _stop_events.pop(skey, None)
    except asyncio.CancelledError:
        stopped = True
        raise
    finally:
        # Always cancel typing indicator
        if typing_task and not typing_task.done():
            typing_task.cancel()
        if not _is_compact:
            _streaming_tasks.pop(skey, None)
        try:
            _get_user_lock(session_user_id).release()
        except RuntimeError:
            pass  # already released by /stop
        # Clean up Telegram messages (must run even on CancelledError)
        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass
        if stopped and live_msg:
            try:
                await live_msg.delete()
            except Exception:
                pass

    # Handle /stop cancellation
    if stopped:
        return

    if response_text is None:
        response_text = "Claude processed the request but returned no text output."

    if not response_text:
        # Silent exit (e.g. bot restart killed the process) — nothing to send
        if live_msg:
            try:
                await live_msg.delete()
            except Exception:
                pass
        return

    # Extract image URLs from response and send as Telegram photos
    response_text, image_urls = _extract_image_urls(response_text)

    # Skip sending if the text was already flushed into a finalized message
    if flushed_text and response_text == flushed_text:
        pass
    elif not response_text and image_urls:
        # Only images, no text — delete live msg if any
        if live_msg:
            try:
                await live_msg.delete()
            except Exception:
                pass
    elif live_msg and streaming:
        try:
            rendered = renderer.render(response_text)
            if len(rendered) <= TELEGRAM_MAX_LENGTH:
                await live_msg.edit_text(
                    rendered,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            else:
                await live_msg.delete()
                await send_rendered(update, response_text, context)
        except Exception:
            try:
                await live_msg.delete()
            except Exception:
                pass
            await send_rendered(update, response_text, context)
    else:
        await send_rendered(update, response_text, context)

    # Send extracted images as Telegram photos
    for img_url in image_urls:
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=img_url,
                message_thread_id=tg_thread_id,
            )
        except Exception:
            logger.warning("Failed to send photo URL: %s", img_url)
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=img_url,
                    message_thread_id=tg_thread_id,
                )
            except Exception:
                pass

    # Context usage warnings and auto-compact
    if not _is_compact:
        sid = get_session_id(chat_id, thread_id, session_user_id)
        ctx = get_context_pct(chat_id, thread_id, session_user_id) if sid else None
        if ctx:
            pct, used, window = ctx
            if pct >= 0.8:
                await update.message.reply_text(
                    f"Context at {pct:.0%} \u2014 auto-compacting\u2026",
                    message_thread_id=tg_thread_id,
                )
                await run_with_streaming(update, context, chat_id, thread_id,
                                         user_id, "/compact", _is_compact=True)
            elif pct >= 0.6:
                await update.message.reply_text(
                    f"Context at {pct:.0%} \u2014 consider using /compact",
                    message_thread_id=tg_thread_id,
                )


# ---------------------------------------------------------------------------
# Message & Media Handlers
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages — route to Claude."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    if not should_respond(update):
        return

    message_text = update.message.text
    if not message_text:
        return

    message_text = strip_bot_mention(message_text)
    if not message_text:
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    logger.info(
        "Message from %s (%d) in chat %d thread %d, length=%d",
        user.username or user.first_name,
        user.id, chat_id, thread_id, len(message_text),
    )
    get_workspace_logger(chat_id).info(
        "Message from user %d (%s), length=%d",
        user.id, user.username or user.first_name, len(message_text),
    )

    claude_msg = get_reply_prefix(update) + message_text
    await queue_message(update, context, chat_id, thread_id, user.id, claude_msg)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages and audio."""
    from bot.transcribe import transcribe

    user = update.effective_user
    if not is_authorized(user.id):
        return

    if not should_respond(update):
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    logger.info(
        "Voice/audio from %s (%d) in chat %d thread %d, duration=%s",
        user.username or user.first_name, user.id,
        chat_id, thread_id, getattr(voice, "duration", "?"),
    )
    get_workspace_logger(chat_id).info(
        "Voice from user %d (%s), duration=%s",
        user.id, user.username or user.first_name, getattr(voice, "duration", "?"),
    )

    workspace = ensure_workspace(chat_id)
    voice_dir = workspace / "uploads" / f"t{thread_id}" / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    ogg_path = voice_dir / f"{voice.file_id}.ogg"

    file = await context.bot.get_file(voice.file_id)
    await file.download_to_drive(ogg_path)

    text = await transcribe(ogg_path)
    caption = update.message.caption or ""
    claude_msg = get_reply_prefix(update) + f'[Voice message transcription]: "{text}"'
    if caption:
        claude_msg += f' User also wrote: "{caption}"'

    await queue_message(update, context, chat_id, thread_id, user.id, claude_msg)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming documents/files."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    if not should_respond(update):
        return

    doc = update.message.document
    if not doc:
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    logger.info(
        "Document from %s (%d) in chat %d thread %d: %s (%s bytes)",
        user.username or user.first_name, user.id,
        chat_id, thread_id, doc.file_name, doc.file_size,
    )
    get_workspace_logger(chat_id).info(
        "Document from user %d: %s (%s bytes)",
        user.id, doc.file_name, doc.file_size,
    )

    workspace = ensure_workspace(chat_id)
    today = datetime.now().strftime("%Y-%m-%d")
    dest_dir = workspace / "uploads" / f"t{thread_id}" / today
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(doc.file_name).name if doc.file_name else f"file_{doc.file_id}"
    dest = dest_dir / safe_name

    file = await context.bot.get_file(doc.file_id)
    await file.download_to_drive(dest)

    caption = update.message.caption or ""
    claude_msg = f"[User attached a file: {dest.relative_to(workspace)} — read it before responding.]"
    if caption:
        claude_msg += f' User says: "{caption}"'

    await queue_message(update, context, chat_id, thread_id, user.id, claude_msg)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming video messages."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    if not should_respond(update):
        return

    video = update.message.video
    if not video:
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    logger.info(
        "Video from %s (%d) in chat %d thread %d: %s (%s bytes)",
        user.username or user.first_name, user.id,
        chat_id, thread_id, video.file_name or video.file_id, video.file_size,
    )
    get_workspace_logger(chat_id).info(
        "Video from user %d: %s (%s bytes)",
        user.id, video.file_name or video.file_id, video.file_size,
    )

    workspace = ensure_workspace(chat_id)
    today = datetime.now().strftime("%Y-%m-%d")
    dest_dir = workspace / "uploads" / f"t{thread_id}" / today
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(video.file_name).name if video.file_name else f"video_{video.file_id}.mp4"
    dest = dest_dir / safe_name

    file = await context.bot.get_file(video.file_id)
    await file.download_to_drive(dest)

    caption = update.message.caption or ""
    claude_msg = f"[User attached a video: {dest.relative_to(workspace)} — read it before responding.]"
    if caption:
        claude_msg += f' User says: "{caption}"'

    await queue_message(update, context, chat_id, thread_id, user.id, claude_msg)


_MAX_IMAGE_DIM = 2048  # Anthropic recommended max dimension
_MAX_IMAGE_BYTES = 3 * 1024 * 1024  # 3MB raw limit (API encodes to base64)


def _normalize_image(path: Path) -> Path:
    """Validate and normalize an image file for the Anthropic API.

    Re-saves as JPEG in RGB mode, resizes if too large.
    Returns the (possibly new) path on success, original path on failure.
    """
    try:
        from PIL import Image
        with Image.open(path) as img:
            # Convert to RGB (drops alpha channel, handles palette modes)
            if img.mode != "RGB":
                img = img.convert("RGB")
            # Resize if either dimension exceeds the limit
            if img.width > _MAX_IMAGE_DIM or img.height > _MAX_IMAGE_DIM:
                img.thumbnail((_MAX_IMAGE_DIM, _MAX_IMAGE_DIM), Image.LANCZOS)
            # Re-save as JPEG to ensure valid format
            new_path = path.with_suffix(".jpg")
            img.save(new_path, format="JPEG", quality=85, optimize=True)
            # If still too large, reduce quality further
            if new_path.stat().st_size > _MAX_IMAGE_BYTES:
                img.save(new_path, format="JPEG", quality=60, optimize=True)
            # Delete original only after new file is confirmed written
            if new_path != path:
                path.unlink(missing_ok=True)
            return new_path
    except Exception as e:
        logger.warning("Image normalization failed for %s: %s", path, e)
        return path


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    if not should_respond(update):
        return

    photos = update.message.photo
    if not photos:
        return

    photo = photos[-1]

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    logger.info(
        "Photo from %s (%d) in chat %d thread %d, size=%dx%d",
        user.username or user.first_name, user.id,
        chat_id, thread_id, photo.width, photo.height,
    )
    get_workspace_logger(chat_id).info(
        "Photo from user %d, size=%dx%d",
        user.id, photo.width, photo.height,
    )

    workspace = ensure_workspace(chat_id)
    today = datetime.now().strftime("%Y-%m-%d")
    dest_dir = workspace / "uploads" / f"t{thread_id}" / today
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"photo_{photo.file_unique_id}.jpg"

    file = await context.bot.get_file(photo.file_id)
    await file.download_to_drive(dest)
    dest = await asyncio.get_event_loop().run_in_executor(None, _normalize_image, dest)

    caption = update.message.caption or ""
    claude_msg = f"[User attached a photo: {dest.relative_to(workspace)} — read it before responding.]"
    if caption:
        claude_msg += f' User says: "{caption}"'

    await queue_message(update, context, chat_id, thread_id, user.id, claude_msg)
