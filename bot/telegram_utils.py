"""Telegram utility helpers."""

from __future__ import annotations

from telegram import Update


def get_thread_id(update: Update) -> int:
    """Get the forum topic thread ID, or 0 for non-forum messages."""
    msg = update.message
    if msg and msg.message_thread_id:
        return msg.message_thread_id
    if update.callback_query and update.callback_query.message:
        cb_msg = update.callback_query.message
        if hasattr(cb_msg, "message_thread_id") and cb_msg.message_thread_id:
            return cb_msg.message_thread_id
    return 0
