"""Message handler — routes incoming text messages to Claude."""

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from bot.auth import authorized
from bot.batching import queue_message
from bot.config import get_thread_id
from bot.logging_setup import get_workspace_logger
from bot.routing import get_reply_prefix, strip_bot_mention

logger = logging.getLogger(__name__)


def _time_prefix() -> str:
    """Return a [HH:MM] time prefix for the current UTC time."""
    return datetime.now(timezone.utc).strftime("[%H:%M] ")


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

    claude_msg = _time_prefix() + get_reply_prefix(update) + message_text
    await queue_message(update, context, chat_id, thread_id, user.id, claude_msg)
