"""Utility commands: /model, /whoami, /files, /clean, /context, /compact."""

import contextlib
import html
import logging
import shutil

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import (
    ADMIN_USER_ID,
    get_claude_model,
    get_thread_id,
    is_authorized,
    set_claude_model,
)
from bot.renderer import split_message
from bot.sessions import get_context_pct, get_session_id, get_usage
from bot.utils import context_bar, format_size
from bot.workspaces import ensure_workspace

logger = logging.getLogger(__name__)

COMMANDS = [
    ("model", "Show or switch the Claude model"),
    ("whoami", "Show what the bot knows about you"),
    ("files", "List files in your workspace"),
    ("clean", "Clean uploaded files"),
    ("context", "Show context usage for current conversation"),
    ("compact", "Compact current conversation to free context"),
]


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current Claude model, or switch it."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    thread_id = get_thread_id(update)
    new_model = " ".join(context.args).strip() if context.args else ""

    if new_model:
        if ADMIN_USER_ID and user.id != ADMIN_USER_ID:
            await update.message.reply_text(
                "Only admin can switch the model.",
                message_thread_id=thread_id or None,
            )
            return

        set_claude_model(new_model)
        await update.message.reply_text(
            f"Model switched to: <code>{html.escape(new_model)}</code>",
            parse_mode=ParseMode.HTML,
            message_thread_id=thread_id or None,
        )
        logger.info("Model changed to %s by user %d", new_model, user.id)
    else:
        current = get_claude_model() or "(default — not set)"
        await update.message.reply_text(
            f"Current model: <code>{html.escape(current)}</code>\n"
            f"Usage: /model <code>model-name</code> to switch",
            parse_mode=ParseMode.HTML,
            message_thread_id=thread_id or None,
        )


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the bot's knowledge about the user (USER.md contents)."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    workspace = ensure_workspace(chat_id)
    user_md = workspace / "USER.md"

    if user_md.exists():
        content = user_md.read_text().strip()
        if content:
            text = f"<b>USER.md</b>:\n<pre>{html.escape(content[:3000])}</pre>"
        else:
            text = "USER.md exists but is empty."
    else:
        text = "USER.md not created yet. Start a conversation and the bot will learn about you."

    try:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, message_thread_id=thread_id or None,
        )
    except Exception:
        await update.message.reply_text(
            content if user_md.exists() and content else text,
            message_thread_id=thread_id or None,
        )


async def cmd_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List files in the workspace."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    workspace = ensure_workspace(chat_id)

    lines = []
    for item in sorted(workspace.rglob("*"), key=lambda p: str(p)):
        if item.is_symlink():
            continue
        rel = item.relative_to(workspace)
        if str(rel).startswith(".claude"):
            continue
        depth = len(rel.parts)
        if depth > 4:
            continue
        indent = "  " * (depth - 1)
        if item.is_dir():
            lines.append(f"{indent}{rel.name}/")
        else:
            try:
                size = item.stat().st_size
            except OSError:
                continue
            lines.append(f"{indent}{rel.name} ({format_size(size)})")

    if not lines:
        text = "Workspace is empty."
    else:
        if len(lines) > 60:
            lines = lines[:60]
            lines.append("... and more files")
        text = f"<b>Workspace files</b>:\n<pre>{html.escape(chr(10).join(lines))}</pre>"

    for chunk in split_message(text):
        try:
            await update.message.reply_text(
                chunk, parse_mode=ParseMode.HTML, message_thread_id=thread_id or None,
            )
        except Exception:
            await update.message.reply_text(chunk, message_thread_id=thread_id or None)


async def cmd_clean(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clean uploaded files from the workspace."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    workspace = ensure_workspace(chat_id)
    uploads_dir = workspace / "uploads"

    if not uploads_dir.exists():
        await update.message.reply_text(
            "No uploads to clean.", message_thread_id=thread_id or None,
        )
        return

    file_count = sum(1 for _ in uploads_dir.rglob("*") if _.is_file())
    if file_count == 0:
        await update.message.reply_text(
            "Uploads directory is empty.", message_thread_id=thread_id or None,
        )
        return

    total_size = sum(f.stat().st_size for f in uploads_dir.rglob("*") if f.is_file())
    size_str = format_size(total_size)

    shutil.rmtree(uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    await update.message.reply_text(
        f"Cleaned {file_count} file(s) ({size_str}).",
        message_thread_id=thread_id or None,
    )
    logger.info("User %d cleaned uploads for chat %d: %d files, %s",
                 user.id, chat_id, file_count, size_str)


async def cmd_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show context/token usage for the current conversation."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    session_uid = user.id if update.effective_chat.type == "private" else 0
    tg_thread_id = thread_id or None

    usage = get_usage(chat_id, thread_id, session_uid)
    if not usage:
        await update.message.reply_text(
            "No usage data yet \u2014 send a message first.",
            message_thread_id=tg_thread_id,
        )
        return

    usage_dict = usage.get("usage")

    lines = ["<b>Context Usage</b>", ""]

    ctx = get_context_pct(chat_id, thread_id, session_uid)
    if ctx:
        pct, used, ctx_window = ctx
        bar = context_bar(used, ctx_window)
        lines.append(f"<code>{bar}</code>")
        lines.append(f"<b>Used:</b> {used:,} / {ctx_window:,} tokens")
        lines.append("")

    # Additional token breakdown
    cache_tok = None
    output_tok = None
    if isinstance(usage_dict, dict):
        cache_tok = (usage_dict.get("cache_read_input_tokens")
                     or usage_dict.get("cacheReadInputTokens"))
        output_tok = usage_dict.get("output_tokens") or usage_dict.get("outputTokens")

    if cache_tok is not None:
        lines.append(f"<b>Cached:</b> {cache_tok:,}")
    if output_tok is not None:
        lines.append(f"<b>Output:</b> {output_tok:,}")

    cost = usage.get("cost")
    if cost is not None:
        lines.append(f"<b>Cost:</b> ${cost:.4f}")

    num_turns = usage.get("num_turns")
    if num_turns is not None:
        lines.append(f"<b>Turns:</b> {num_turns}")

    duration_ms = usage.get("duration_ms")
    if duration_ms is not None:
        secs = duration_ms / 1000
        lines.append(f"<b>Duration:</b> {secs:.1f}s")

    sid = get_session_id(chat_id, thread_id, session_uid)
    if sid:
        lines.extend(["", f"<b>Session:</b> <code>{sid[:16]}...</code>"])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        message_thread_id=tg_thread_id,
    )


async def cmd_compact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Compact the current conversation to free context."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    session_uid = user.id if update.effective_chat.type == "private" else 0
    tg_thread_id = thread_id or None

    sid = get_session_id(chat_id, thread_id, session_uid)
    if not sid:
        await update.message.reply_text(
            "No active session to compact.",
            message_thread_id=tg_thread_id,
        )
        return

    status_msg = await update.message.reply_text(
        "Compacting conversation\u2026",
        message_thread_id=tg_thread_id,
    )

    from bot.streaming import run_with_streaming
    await run_with_streaming(update, context, chat_id, thread_id, user.id, "/compact",
                             _is_compact=True)

    with contextlib.suppress(Exception):
        await status_msg.edit_text("Compaction complete.")


def register(app: Application) -> None:
    """Register utility command handlers."""
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("files", cmd_files))
    app.add_handler(CommandHandler("clean", cmd_clean))
    app.add_handler(CommandHandler("context", cmd_context))
    app.add_handler(CommandHandler("compact", cmd_compact))
