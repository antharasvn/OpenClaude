"""Telegram message/media handlers + batching + streaming UI.

This module is now a thin facade. The actual implementations live in:
  - bot.attachments     — file marker parsing, image URL extraction
  - bot.telegram_sender — send_file_group, send_single_file, send_rendered
  - bot.media           — normalize_image
  - bot.routing         — should_respond, strip_bot_mention, get_reply_prefix
  - bot.batching        — queue_message, _flush_batch
  - bot.media_handlers  — handle_photo, handle_voice, handle_document, handle_video
  - bot.streaming_session — StreamingSession class
"""

import asyncio
import contextlib
import html
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# --- Re-exports from extracted modules (for backward compatibility) ---
from bot.attachments import (  # noqa: F401
    extract_image_urls as _extract_image_urls,
)
from bot.auth import authorized
from bot.batching import queue_message  # noqa: F401
from bot.claude import stream_claude
from bot.config import (
    ALL_TOOLS,
    get_thread_id,
    is_authorized,
)
from bot.logging_setup import get_workspace_logger
from bot.media_handlers import (  # noqa: F401
    handle_document,
    handle_photo,
    handle_video,
    handle_voice,
)
from bot.process import kill_active_proc
from bot.renderer import TelegramRenderer
from bot.routing import (  # noqa: F401
    get_reply_prefix,
    should_respond,
    strip_bot_mention,
)
from bot.sdk_session import sdk_session_manager
from bot.sessions import clear_session, get_context_pct, get_session_id, load_sessions, session_key
from bot.telegram_sender import (  # noqa: F401
    send_file_group as _send_file_group,
)
from bot.workspaces import get_working_dir

logger = logging.getLogger(__name__)

# --- Module-level state (kept here for now) ---

renderer = TelegramRenderer()

TYPING_INTERVAL = 4  # seconds between typing indicator refreshes

# BOT_USERNAME is set from routing module; kept as alias for app.py compatibility
import bot.routing as _routing  # noqa: E402

BOT_USERNAME = _routing.BOT_USERNAME


def _set_bot_username(username: str) -> None:
    """Set bot username in both this module and routing module."""
    global BOT_USERNAME
    BOT_USERNAME = username
    _routing.BOT_USERNAME = username


# Per-user locks to prevent concurrent Claude calls for the same user
_user_locks: dict[str, asyncio.Lock] = {}

# Per-session stop events for /stop command
_stop_events: dict[str, asyncio.Event] = {}

# Per-session streaming task references for /stop cancellation
_streaming_tasks: dict[str, asyncio.Task] = {}


def _get_user_lock(skey: str) -> asyncio.Lock:
    if skey not in _user_locks:
        _user_locks[skey] = asyncio.Lock()
    return _user_locks[skey]


async def _typing_loop(bot, chat_id: int, thread_id: int | None = None) -> None:
    """Send 'typing' chat action periodically until cancelled."""
    try:
        while True:
            try:
                await bot.send_chat_action(
                    chat_id=chat_id,
                    action="typing",
                    message_thread_id=thread_id if thread_id else None,
                )
            except Exception:
                logger.debug("typing indicator send failed for chat %d", chat_id)
            await asyncio.sleep(TYPING_INTERVAL)
    except asyncio.CancelledError:
        pass


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
    """Handle /new command -- clear session and start fresh."""
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
    """Handle /status command -- show user ID and session info."""
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
        "<b>OpenClaude Status</b>",
        "",
        f"<b>User ID:</b> <code>{user.id}</code>",
        f"<b>Username:</b> @{html.escape(user.username) if user.username else 'N/A'}",
        f"<b>Session:</b> <code>{sid or 'None'}</code>",
    ]

    if updated := user_data.get("updated_at"):
        status_lines.append(f"<b>Last active:</b> {updated}")

    chat_dir = get_working_dir(chat_id)
    status_lines.extend([
        "",
        f"<b>Working dir:</b> <code>{chat_dir}</code>",
        f"<b>Allowed tools:</b> {ALL_TOOLS}",
    ])

    await update.message.reply_text(
        "\n".join(status_lines),
        parse_mode=ParseMode.HTML,
        message_thread_id=thread_id or None,
    )


async def _force_stop_session(skey: str, chat_id: int, thread_id: int, session_uid: int) -> None:
    """Kill subprocess, cancel streaming task, and force-cleanup lock/streams."""
    from bot.streams import remove_active_stream

    stop_event = _stop_events.get(skey)
    if stop_event:
        stop_event.set()

    # Hard-kill the subprocess tree
    sdk_session = sdk_session_manager.get(skey)
    if sdk_session:
        sdk_session.hard_kill()
        if sdk_session.connected:
            await sdk_session.disconnect()
        sdk_session_manager.pop(skey)

    kill_active_proc(skey)

    # Cancel the streaming asyncio task so finally blocks run
    task = _streaming_tasks.get(skey)
    if task and not task.done():
        task.cancel()
        with contextlib.suppress(TimeoutError, asyncio.CancelledError, Exception):
            await asyncio.wait_for(task, timeout=5)

    # Force cleanup in case the task didn't finish or clean up properly
    _streaming_tasks.pop(skey, None)
    _stop_events.pop(skey, None)
    remove_active_stream(chat_id, thread_id, session_uid)
    lock = _user_locks.get(skey)
    if lock and lock.locked():
        with contextlib.suppress(RuntimeError):
            lock.release()


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stop command -- cancel current Claude generation."""
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
# Streaming UI
# ---------------------------------------------------------------------------

async def run_with_streaming(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             chat_id: int, thread_id: int, user_id: int,
                             claude_message: str, _is_compact: bool = False) -> None:
    """Stream Claude output, show tool progress, then send final response.

    All streaming state and event handling is delegated to StreamingSession.
    This function manages the lifecycle: lock acquisition, typing indicator,
    event loop, and cleanup.
    """
    from bot.streaming_session import StreamingSession
    from commands.config import get_streaming, get_verbose

    session_user_id = user_id if update.effective_chat.type == "private" else 0
    tg_thread_id = thread_id or None
    streaming = get_streaming(chat_id, thread_id)
    show_tools = get_verbose(chat_id, thread_id)

    session = StreamingSession(
        update=update,
        context=context,
        chat_id=chat_id,
        thread_id=thread_id,
        tg_thread_id=tg_thread_id,
        streaming=streaming,
        show_tools=show_tools,
    )
    # Store session_user_id for usage tracking inside _on_result
    session.session_user_id = session_user_id

    chat_working_dir = get_working_dir(chat_id)
    skey = session_key(chat_id, thread_id, session_user_id)

    typing_task = None

    try:
        await asyncio.wait_for(_get_user_lock(skey).acquire(), timeout=300)
    except TimeoutError:
        logger.error("Lock acquisition timed out for user %d in chat %d", session_user_id, chat_id)
        with contextlib.suppress(Exception):
            await update.message.reply_text(
                "Still processing a previous request. Use /stop to cancel it.",
                message_thread_id=tg_thread_id,
            )
        return

    try:
        # Only register task/stop_event for primary calls -- auto-compact is nested
        # and must not clobber the outer call's registration.
        if not _is_compact:
            _streaming_tasks[skey] = asyncio.current_task()
        stop_event = asyncio.Event()
        if not _is_compact:
            _stop_events[skey] = stop_event

        # Start typing indicator -- runs until cancelled
        typing_task = asyncio.create_task(_typing_loop(context.bot, chat_id, tg_thread_id))
        try:
            async for event in stream_claude(claude_message, chat_id, thread_id, session_user_id,
                                             working_dir=chat_working_dir, verbose=streaming,
                                             stop_event=stop_event,
                                             real_user_id=user_id):
                etype = event.get("type")

                # Stop typing once visible output is streaming
                if etype == "partial" and typing_task and not typing_task.done():
                    typing_task.cancel()

                await session.handle_event(event)

            # Final flush of any buffered live text
            await session.flush_live()
        finally:
            if not _is_compact:
                _stop_events.pop(skey, None)
    except asyncio.CancelledError:
        session.stopped = True
        raise
    finally:
        # Always cancel typing indicator
        if typing_task and not typing_task.done():
            typing_task.cancel()
        if not _is_compact:
            _streaming_tasks.pop(skey, None)
        with contextlib.suppress(RuntimeError):
            _get_user_lock(skey).release()
        # Clean up Telegram messages (must run even on CancelledError)
        await session.cleanup_status()
        if session.stopped:
            await session.cleanup_on_stop()

    # Handle /stop cancellation
    if session.stopped:
        return

    # Finalize: delete intermediates, send final response, files, images
    await session.finalize_response()

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
# Message Handler
# ---------------------------------------------------------------------------

@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages -- route to Claude."""
    user = update.effective_user
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
