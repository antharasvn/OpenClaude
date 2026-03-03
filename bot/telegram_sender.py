"""Telegram message sending — file groups, single files, rendered markdown."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import get_thread_id
from bot.renderer import TelegramRenderer, split_message

if TYPE_CHECKING:
    from bot.types import FileAttachment

logger = logging.getLogger(__name__)

# Module-level renderer instance
renderer = TelegramRenderer()


async def send_file_group(
    bot,
    chat_id: int,
    files: list[FileAttachment],
    thread_id: int | None = None,
) -> None:
    """Send a group of files as a Telegram media group when possible.

    Telegram constraints: photos+videos can mix; documents only with
    documents; audio only with audio.  Falls back to individual sends
    for incompatible mixes or single files.
    """
    from telegram import InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument

    if len(files) == 1:
        await send_single_file(bot, chat_id, files[0], thread_id)
        return

    media_types = {f.media_type for f in files}
    can_group = (
        media_types <= {"photo", "video"}
        or media_types == {"document"}
        or media_types == {"audio"}
    )

    if can_group:
        type_map = {
            "photo": InputMediaPhoto,
            "video": InputMediaVideo,
            "audio": InputMediaAudio,
            "document": InputMediaDocument,
        }
        media = []
        for f in files:
            cls = type_map[f.media_type]
            media.append(cls(media=open(f.path, "rb"), caption=f.caption or None))
        try:
            await bot.send_media_group(
                chat_id=chat_id, media=media, message_thread_id=thread_id,
            )
        except Exception:
            logger.warning("Media group send failed, falling back to individual sends")
            for f in files:
                try:
                    await send_single_file(bot, chat_id, f, thread_id)
                except Exception:
                    logger.warning("Failed to send file: %s", f.path)
        finally:
            for m in media:
                try:
                    m.media.close()
                except Exception:
                    pass
    else:
        # Mixed types that can't be grouped -- send individually
        for f in files:
            try:
                await send_single_file(bot, chat_id, f, thread_id)
            except Exception:
                logger.warning("Failed to send file: %s", f.path)


async def send_single_file(
    bot,
    chat_id: int,
    file_info: FileAttachment,
    thread_id: int | None = None,
) -> None:
    """Send a single local file to Telegram using the appropriate media method."""
    path = file_info.path
    caption = file_info.caption or None
    media_type = file_info.media_type

    with open(path, "rb") as f:
        if media_type == "photo":
            await bot.send_photo(chat_id=chat_id, photo=f, caption=caption,
                                 message_thread_id=thread_id)
        elif media_type == "video":
            await bot.send_video(chat_id=chat_id, video=f, caption=caption,
                                 message_thread_id=thread_id)
        elif media_type == "audio":
            await bot.send_audio(chat_id=chat_id, audio=f, caption=caption,
                                 message_thread_id=thread_id)
        else:
            await bot.send_document(chat_id=chat_id, document=f, caption=caption,
                                    message_thread_id=thread_id)


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


async def send_rendered_collect(
    update: Update,
    text: str,
    context: ContextTypes.DEFAULT_TYPE,
    tg_thread_id: int | None = None,
) -> list:
    """Like send_rendered but returns the list of sent Message objects."""
    md_chunks = split_message(text)
    sent: list = []

    for md_chunk in md_chunks:
        chunk = renderer.render(md_chunk)
        try:
            msg = await update.message.reply_text(
                chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                message_thread_id=tg_thread_id,
            )
            sent.append(msg)
        except Exception:
            logger.warning("HTML send failed for chunk, falling back to plain text")
            plain = re.sub(r"<[^>]+>", "", chunk)
            plain_chunks = split_message(plain)
            for pc in plain_chunks:
                try:
                    msg = await update.message.reply_text(
                        pc,
                        message_thread_id=tg_thread_id,
                    )
                    sent.append(msg)
                except Exception:
                    logger.warning("Plain text fallback also failed")

    return sent
