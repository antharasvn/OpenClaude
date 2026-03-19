"""Message batching — accumulate rapid-fire messages before sending to Claude."""

import asyncio
import contextlib
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import BATCH_WINDOW
from bot.sessions import session_key

logger = logging.getLogger(__name__)

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
    """Flush the batch buffer -- combine messages and send to Claude."""
    from bot.streaming import run_with_streaming

    messages = _batch_buffers.pop(key, [])
    update_ctx = _batch_updates.pop(key, None)
    meta = _batch_meta.pop(key, None)
    _batch_timers.pop(key, None)

    if not messages or not update_ctx or not meta:
        return

    update, context = update_ctx
    chat_id, thread_id, user_id = meta

    combined = messages[0] if len(messages) == 1 else "\n\n".join(messages)

    try:
        await run_with_streaming(update, context, chat_id, thread_id, user_id, combined)
    except Exception:
        logger.exception("_flush_batch failed for key=%s", key)
        with contextlib.suppress(Exception):
            tg_thread_id = thread_id if thread_id else None
            await update.message.reply_text(
                "Something went wrong processing your message. Please try again.",
                message_thread_id=tg_thread_id,
            )


async def flush_all_batches() -> None:
    """Flush all pending batch buffers. Call on shutdown."""
    keys = list(_batch_buffers.keys())
    for key in keys:
        timer = _batch_timers.get(key)
        if timer:
            timer.cancel()
        try:
            await _flush_batch(key)
        except Exception:
            logger.exception("flush_all_batches: failed for key=%s", key)
