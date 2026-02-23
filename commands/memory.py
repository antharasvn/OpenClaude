"""Memory commands: /forget, /memory, /save, /remember, /history, /daily."""

import html
import re
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import is_authorized, get_thread_id
from bot.renderer import split_message
from bot.workspaces import ensure_workspace
from bot.handlers import run_with_streaming

# (command_name, description) — used by /start listing
COMMANDS = [
    ("memory", "Show long-term memory"),
    ("daily", "Show today's daily logs (or /daily YYYY-MM-DD)"),
    ("save", "Save conversation summary (/save <filename>)"),
    ("remember", "Save a note to long-term memory"),
    ("forget", "Ask Claude to remove something from memory"),
    ("history", "Summarize recent conversation"),
]


async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show contents of workspace memory and topic memory."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    workspace = ensure_workspace(chat_id)

    sections = []

    # Workspace memory
    mem_file = workspace / "memory" / "MEMORY.md"
    if mem_file.exists():
        content = mem_file.read_text().strip()
        if content:
            sections.append(
                f"<b>Workspace memory</b> (MEMORY.md):\n"
                f"<pre>{html.escape(content[:3000])}</pre>"
            )
        else:
            sections.append("<b>Workspace memory</b> (MEMORY.md): <i>empty</i>")
    else:
        sections.append("<b>Workspace memory</b>: <i>not created yet</i>")

    # Topic memory (only show separately for non-zero TID)
    if thread_id != 0:
        topic_mem = workspace / "memory" / f"t{thread_id}" / "MEMORY.md"
        if topic_mem.exists():
            content = topic_mem.read_text().strip()
            if content:
                sections.append(
                    f"<b>Topic memory</b> (t{thread_id}/MEMORY.md):\n"
                    f"<pre>{html.escape(content[:3000])}</pre>"
                )
            else:
                sections.append(f"<b>Topic memory</b> (t{thread_id}/MEMORY.md): <i>empty</i>")
        else:
            sections.append(f"<b>Topic memory</b> (t{thread_id}): <i>not created yet</i>")

    text = "\n\n".join(sections)
    tg_thread = thread_id or None
    for chunk in split_message(text):
        try:
            await update.message.reply_text(
                chunk, parse_mode=ParseMode.HTML, message_thread_id=tg_thread,
            )
        except Exception:
            await update.message.reply_text(chunk, message_thread_id=tg_thread)


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show daily log files for today (or a specific date)."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    workspace = ensure_workspace(chat_id)
    mem_dir = workspace / "memory"

    # Accept optional date argument, default to today
    date_str = context.args[0] if context.args else f"{datetime.now():%Y-%m-%d}"
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        await update.message.reply_text(
            "Invalid date format. Use YYYY-MM-DD.",
            message_thread_id=thread_id or None,
        )
        return
    daily_dir = mem_dir / f"t{thread_id}" / date_str

    if not daily_dir.exists() or not daily_dir.is_dir():
        await update.message.reply_text(
            f"No daily logs for <b>{html.escape(date_str)}</b> (t{thread_id}).",
            parse_mode=ParseMode.HTML,
            message_thread_id=thread_id or None,
        )
        return

    md_files = sorted(daily_dir.glob("*.md"))
    if not md_files:
        await update.message.reply_text(
            f"No daily logs for <b>{html.escape(date_str)}</b> (t{thread_id}).",
            parse_mode=ParseMode.HTML,
            message_thread_id=thread_id or None,
        )
        return

    sections = []
    for f in md_files:
        content = f.read_text().strip()
        if content:
            sections.append(
                f"<b>{html.escape(f.stem)}</b>:\n"
                f"<pre>{html.escape(content[:1500])}</pre>"
            )
        else:
            sections.append(f"<b>{html.escape(f.stem)}</b>: <i>empty</i>")

    header = f"<b>Daily logs — {html.escape(date_str)} (t{thread_id})</b>\n\n"
    text = header + "\n\n".join(sections)
    tg_thread = thread_id or None

    for chunk in split_message(text):
        try:
            await update.message.reply_text(
                chunk, parse_mode=ParseMode.HTML, message_thread_id=tg_thread,
            )
        except Exception:
            await update.message.reply_text(chunk, message_thread_id=tg_thread)


async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save a conversation summary to a named daily log file via Claude."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    filename = context.args[0] if context.args else ""
    if not filename:
        await update.message.reply_text("Usage: /save <filename>")
        return

    # Strip .md extension if user added it
    if filename.endswith(".md"):
        filename = filename[:-3]

    if not re.match(r'^[\w\-]+$', filename):
        await update.message.reply_text(
            "Filename must be alphanumeric (a-z, 0-9, -, _).",
            message_thread_id=get_thread_id(update) or None,
        )
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    today = f"{datetime.now():%Y-%m-%d}"

    prompt = (
        f"[System command: /save {filename}]\n"
        f"Summarize this conversation and save it to "
        f"memory/t{thread_id}/{today}/{filename}.md\n\n"
        f"Create the directory if needed (mkdir -p). Write a concise but useful "
        f"summary of what was discussed, decided, and done. Use markdown formatting. "
        f"Keep it focused — this is a daily working note, not a transcript."
    )

    await run_with_streaming(update, context, chat_id, thread_id, user.id, prompt)


async def cmd_remember(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save a note to memory. Topic memory if in a topic, workspace memory otherwise."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    note = " ".join(context.args) if context.args else ""
    if not note:
        await update.message.reply_text("Usage: /remember <note>")
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    workspace = ensure_workspace(chat_id)

    if thread_id != 0:
        # Write to topic memory
        mem = workspace / "memory" / f"t{thread_id}" / "MEMORY.md"
        label = f"topic memory (t{thread_id})"
    else:
        # Write to workspace memory
        mem = workspace / "memory" / "MEMORY.md"
        label = "workspace memory"

    mem.parent.mkdir(parents=True, exist_ok=True)

    date = datetime.now().strftime("%Y-%m-%d")
    entry = f"- [{date}] {note}\n"

    with open(mem, "a") as f:
        f.write(entry)

    await update.message.reply_text(
        f"Saved to {label}.",
        message_thread_id=thread_id or None,
    )


async def cmd_forget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask Claude to intelligently remove something from memory files."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    what = " ".join(context.args) if context.args else ""
    if not what:
        await update.message.reply_text("Usage: /forget <what to forget>")
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    prompt = (
        f"[System command: /forget]\n"
        f"The user wants you to remove the following from your memory files: \"{what}\"\n\n"
        f"Read your memory files (memory/MEMORY.md, memory/t{thread_id}/MEMORY.md, "
        f"memory/t{thread_id}/**/*.md) and remove any entries matching what the user "
        f"described. Use the Edit tool to surgically remove only the relevant lines. "
        f"Then confirm what you removed."
    )

    await run_with_streaming(update, context, chat_id, thread_id, user.id, prompt)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask Claude to summarize the recent conversation."""
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    prompt = (
        "[System command: /history]\n"
        "The user wants a summary of this conversation. "
        "Provide a concise summary of the key topics discussed, decisions made, "
        "and any pending items. Keep it brief — this is for quick reference."
    )

    await run_with_streaming(update, context, chat_id, thread_id, user.id, prompt)


def register(app: Application) -> None:
    """Register memory command handlers."""
    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("remember", cmd_remember))
    app.add_handler(CommandHandler("forget", cmd_forget))
    app.add_handler(CommandHandler("history", cmd_history))
