"""Config commands: /stream, /verbose, /respond — with inline keyboard toggles."""

import json
import logging
from pathlib import Path
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from bot.config import SCRIPT_DIR, is_authorized, get_thread_id

logger = logging.getLogger(__name__)

COMMANDS = [
    ("stream", "Toggle live streaming of Claude's response"),
    ("verbose", "Toggle tool usage display"),
    ("respond", "Set group response mode (mention/all)"),
]

# ---------------------------------------------------------------------------
# Persistent Settings (per chat/thread)
# ---------------------------------------------------------------------------

_SETTINGS_FILE = None  # Set lazily


def _settings_file() -> Path:
    global _SETTINGS_FILE
    if _SETTINGS_FILE is None:
        _SETTINGS_FILE = SCRIPT_DIR / ".chat-settings.json"
    return _SETTINGS_FILE


_settings_cache: dict | None = None
_settings_mtime: float = 0.0


def _load_settings() -> dict:
    """Load settings with mtime-based caching to avoid repeated file reads."""
    global _settings_cache, _settings_mtime
    f = _settings_file()
    try:
        current_mtime = f.stat().st_mtime
    except OSError:
        return _settings_cache if _settings_cache is not None else {}

    if _settings_cache is not None and current_mtime == _settings_mtime:
        return _settings_cache

    try:
        _settings_cache = json.loads(f.read_text())
        _settings_mtime = current_mtime
        return _settings_cache
    except (json.JSONDecodeError, OSError):
        return _settings_cache if _settings_cache is not None else {}


def _save_settings(settings: dict) -> None:
    global _settings_cache, _settings_mtime
    import os
    import tempfile
    f = _settings_file()
    try:
        fd, tmp_path = tempfile.mkstemp(dir=f.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as fh:
            json.dump(settings, fh, indent=2)
        os.replace(tmp_path, f)
    except OSError:
        try:
            f.write_text(json.dumps(settings, indent=2))
        except OSError as e:
            logger.error("Failed to save chat settings: %s", e)
    # Update cache immediately after save
    _settings_cache = settings
    try:
        _settings_mtime = f.stat().st_mtime
    except OSError:
        _settings_mtime = 0.0


def _setting_key(chat_id: int, thread_id: int) -> str:
    return f"{chat_id}:{thread_id}"


def _get_setting(chat_id: int, thread_id: int, name: str, default: Any = None) -> Any:
    """Get a single setting value for a chat/thread."""
    settings = _load_settings()
    key = _setting_key(chat_id, thread_id)
    return settings.get(key, {}).get(name, default)


def _set_setting(chat_id: int, thread_id: int, name: str, value: Any) -> None:
    settings = _load_settings()
    key = _setting_key(chat_id, thread_id)
    settings.setdefault(key, {})[name] = value
    _save_settings(settings)


# Public getters used by other modules
def get_streaming(chat_id: int, thread_id: int) -> bool:
    """Get live streaming setting for a chat/thread."""
    return _get_setting(chat_id, thread_id, "streaming", False)


def get_verbose(chat_id: int, thread_id: int) -> bool:
    """Get verbose (tool progress) setting for a chat/thread. Default: ON."""
    return _get_setting(chat_id, thread_id, "verbose", True)


def get_respond_mode(chat_id: int, thread_id: int) -> str:
    """Get response mode for a chat/thread: 'mention' or 'all'."""
    return _get_setting(chat_id, thread_id, "respond_mode", "all")


# ---------------------------------------------------------------------------
# ToggleSetting — generic on/off toggle with inline keyboard
# ---------------------------------------------------------------------------

class ToggleSetting:
    """Reusable on/off toggle with persistent storage and inline keyboard.

    Reduces the per-setting boilerplate from ~60 lines to a declaration.
    """

    def __init__(
        self,
        key: str,
        label: str,
        default: bool,
        on_desc: str,
        off_desc: str,
    ) -> None:
        self.key = key
        self.label = label
        self.default = default
        self.on_desc = on_desc
        self.off_desc = off_desc

    def get(self, chat_id: int, thread_id: int) -> bool:
        return _get_setting(chat_id, thread_id, self.key, self.default)

    def set(self, chat_id: int, thread_id: int, value: bool) -> None:
        _set_setting(chat_id, thread_id, self.key, value)

    def text(self, is_on: bool) -> str:
        state = "ON" if is_on else "OFF"
        desc = self.on_desc if is_on else self.off_desc
        return f"<b>{self.label}:</b> {state}\n\n{desc}"

    def keyboard(self, is_on: bool, chat_id: int, thread_id: int) -> InlineKeyboardMarkup:
        on_label = "\u2713 ON" if is_on else "ON"
        off_label = "\u2713 OFF" if not is_on else "OFF"
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(on_label, callback_data=f"{self.key}:on:{chat_id}:{thread_id}"),
            InlineKeyboardButton(off_label, callback_data=f"{self.key}:off:{chat_id}:{thread_id}"),
        ]])

    async def command_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not is_authorized(user.id):
            return

        chat_id = update.effective_chat.id
        thread_id = get_thread_id(update)
        is_on = self.get(chat_id, thread_id)

        await update.message.reply_text(
            self.text(is_on),
            parse_mode=ParseMode.HTML,
            reply_markup=self.keyboard(is_on, chat_id, thread_id),
            message_thread_id=thread_id or None,
        )

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not is_authorized(query.from_user.id):
            await query.answer("Unauthorized", show_alert=True)
            return
        await query.answer()

        parts = query.data.split(":")
        if len(parts) != 4:
            return
        _, action, chat_id_str, thread_id_str = parts
        try:
            chat_id = int(chat_id_str)
            thread_id = int(thread_id_str)
        except ValueError:
            return

        new_value = action == "on"
        self.set(chat_id, thread_id, new_value)

        await query.edit_message_text(
            self.text(new_value),
            parse_mode=ParseMode.HTML,
            reply_markup=self.keyboard(new_value, chat_id, thread_id),
        )


# --- Concrete toggle instances ---

_stream_toggle = ToggleSetting(
    key="streaming",
    label="Streaming",
    default=False,
    on_desc="Response appears live as Claude types, then gets replaced with the final formatted version.",
    off_desc="Tool progress is shown while working, then the full response appears at once.",
)

_verbose_toggle = ToggleSetting(
    key="verbose",
    label="Tool display",
    default=True,
    on_desc="Shows tool usage while Claude is working (reading files, running commands, etc.).",
    off_desc="No tool progress shown \u2014 only the final response.",
)


# ---------------------------------------------------------------------------
# /respond — group response mode (multi-value, not a simple toggle)
# ---------------------------------------------------------------------------

def _respond_keyboard(mode: str, chat_id: int, thread_id: int) -> InlineKeyboardMarkup:
    mention_label = ("\u2713 " if mode == "mention" else "") + "Mention only"
    all_label = ("\u2713 " if mode == "all" else "") + "All messages"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(mention_label, callback_data=f"respond:mention:{chat_id}:{thread_id}"),
        InlineKeyboardButton(all_label, callback_data=f"respond:all:{chat_id}:{thread_id}"),
    ]])


def _respond_text(mode: str) -> str:
    if mode == "all":
        desc = "Bot responds to <b>every message</b> in this thread."
    else:
        desc = "Bot responds only when <b>@mentioned</b> or <b>replied to</b>."
    return f"<b>Response mode:</b> {mode}\n\n{desc}"


async def cmd_respond(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_authorized(user.id):
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    if update.effective_chat.type == "private":
        await update.message.reply_text("Response mode only applies to group chats.")
        return

    mode = get_respond_mode(chat_id, thread_id)

    await update.message.reply_text(
        _respond_text(mode),
        parse_mode=ParseMode.HTML,
        reply_markup=_respond_keyboard(mode, chat_id, thread_id),
        message_thread_id=thread_id or None,
    )


async def callback_respond(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not is_authorized(query.from_user.id):
        await query.answer("Unauthorized", show_alert=True)
        return
    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 4:
        return
    _, mode, chat_id_str, thread_id_str = parts
    try:
        chat_id = int(chat_id_str)
        thread_id = int(thread_id_str)
    except ValueError:
        return

    if mode not in ("mention", "all"):
        return

    _set_setting(chat_id, thread_id, "respond_mode", mode)

    await query.edit_message_text(
        _respond_text(mode),
        parse_mode=ParseMode.HTML,
        reply_markup=_respond_keyboard(mode, chat_id, thread_id),
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register(app: Application) -> None:
    app.add_handler(CommandHandler("stream", _stream_toggle.command_handler))
    app.add_handler(CommandHandler("verbose", _verbose_toggle.command_handler))
    app.add_handler(CommandHandler("respond", cmd_respond))
    app.add_handler(CallbackQueryHandler(_stream_toggle.callback_handler, pattern=r"^streaming:"))
    app.add_handler(CallbackQueryHandler(_verbose_toggle.callback_handler, pattern=r"^verbose:"))
    app.add_handler(CallbackQueryHandler(callback_respond, pattern=r"^respond:"))
