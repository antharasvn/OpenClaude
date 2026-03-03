"""Telegram media handlers — photo, voice, document, video."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.auth import authorized
from bot.config import get_thread_id
from bot.logging_setup import get_workspace_logger
from bot.routing import get_reply_prefix
from bot.batching import queue_message
from bot.media import normalize_image
from bot.workspaces import ensure_workspace

logger = logging.getLogger(__name__)


@authorized
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos."""
    user = update.effective_user
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
    dest = await asyncio.get_event_loop().run_in_executor(None, normalize_image, dest)

    caption = update.message.caption or ""
    claude_msg = f"[User attached a photo: {dest.relative_to(workspace)} — read it before responding.]"
    if caption:
        claude_msg += f' User says: "{caption}"'

    await queue_message(update, context, chat_id, thread_id, user.id, claude_msg)


@authorized
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages and audio."""
    from bot.transcribe import transcribe

    user = update.effective_user
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


@authorized
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming documents/files."""
    user = update.effective_user
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


@authorized
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming video messages."""
    user = update.effective_user
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
