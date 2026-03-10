"""StreamingSession — encapsulates all state and event handling for a single
streaming Claude response.

Extracted from the monolithic run_with_streaming() in handlers.py (Phase 3.1).
This is a pure structural refactoring — behavior is identical.
"""

import asyncio
import contextlib
import logging
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.attachments import clean_file_markers
from bot.config import TELEGRAM_MAX_LENGTH
from bot.formatting import finished_line
from bot.logging_setup import infra_logger
from bot.renderer import TelegramRenderer, find_overflow_split

logger = logging.getLogger(__name__)

# Module-level renderer instance (shared)
renderer = TelegramRenderer()

# Live-edit throttle interval (seconds)
LIVE_EDIT_INTERVAL = 3.0


class StreamingSession:
    """Holds all mutable state for a single streaming response cycle.

    Replaces the ~20 local variables and nested closures that previously
    lived inside run_with_streaming().
    """

    def __init__(
        self,
        update: Update | None = None,
        context: ContextTypes.DEFAULT_TYPE | None = None,
        *,
        bot=None,
        chat_id: int,
        thread_id: int,
        tg_thread_id: int | None,
        streaming: bool,
        show_tools: bool,
    ) -> None:
        self.update = update
        self.context = context
        self.chat_id = chat_id
        self.thread_id = thread_id
        self.tg_thread_id = tg_thread_id
        self.streaming = streaming
        self.show_tools = show_tools

        # Unified bot reference
        if update is not None:
            self._bot = context.bot
            self._bot_only = False
        elif bot is not None:
            self._bot = bot
            self._bot_only = True
        else:
            raise ValueError("Either (update, context) or bot must be provided")

        # Tool-status message state
        self.status_msg = None
        self.finished_lines: list[str] = []
        self.current_active: str = ""
        self.last_edit_time: float = 0

        # Live streaming message state
        self.live_msg = None           # current Telegram message being edited with ✍️
        self.live_text: str = ""       # all accumulated partial text
        self.sent_offset: int = 0      # chars of live_text already in finalized messages
        self.finalized_msgs: list = [] # finalized Telegram messages (for /stop cleanup)
        self.last_live_edit: float = 0

        # Speculative / intermediate message tracking
        self._speculative: list = []         # messages since last tool_use
        self._speculative_sent_len: int = 0  # chars sent via non-streaming text_blocks

        # Flood control
        self.flood_until: float = 0

        # Final result
        self.response_text: str | None = None
        self.stopped: bool = False

    # ------------------------------------------------------------------
    # Sending helpers
    # ------------------------------------------------------------------

    async def _send_new_message(self, text: str, **kwargs) -> object:
        """Send a new message via either update.message.reply_text or bot.send_message."""
        if self._bot_only:
            return await self._bot.send_message(
                chat_id=self.chat_id,
                text=text,
                message_thread_id=self.tg_thread_id or None,
                **kwargs,
            )
        return await self.update.message.reply_text(
            text=text,
            message_thread_id=self.tg_thread_id,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    async def handle_event(self, event: dict) -> None:
        """Dispatch a single stream event to the appropriate handler."""
        etype = event.get("type")

        if etype == "text_block":
            await self._on_text_block(event)
        elif etype == "tool_use":
            await self._on_tool_use(event)
        elif etype == "tool_result":
            await self._on_tool_result(event)
        elif etype == "partial":
            await self._on_partial(event)
        elif etype == "result":
            self._on_result(event)
        elif etype == "error":
            self.response_text = event.get("text", "An error occurred.")
        elif etype == "silent":
            self.response_text = ""
        elif etype == "stopped":
            self.stopped = True

    # ------------------------------------------------------------------
    # Per-event-type handlers
    # ------------------------------------------------------------------

    async def _on_text_block(self, event: dict) -> None:
        """Handle a completed text block (before tool use or at stream end)."""
        block_text = event["text"]
        if self.live_msg:
            chunk_md = self.live_text[self.sent_offset:]
            display_md = clean_file_markers(chunk_md)
            if display_md:
                try:
                    rendered = renderer.render(display_md)
                    await self.live_msg.edit_text(
                        rendered[:TELEGRAM_MAX_LENGTH],
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    )
                except Exception:
                    pass
                self.finalized_msgs.append(self.live_msg)
                self._speculative.append(self.live_msg)
            else:
                # Only 📎 markers, no real text — delete the message
                with contextlib.suppress(Exception):
                    await self.live_msg.delete()
        elif block_text:
            # No streaming — send block directly (strip 📎)
            display_text = clean_file_markers(block_text)
            if display_text:
                sent_msgs = await self._send_rendered_collect(display_text)
                self.finalized_msgs.extend(sent_msgs)
                self._speculative.extend(sent_msgs)
                self._speculative_sent_len += len(block_text)
        self.sent_offset = len(self.live_text)
        self.live_msg = None

    async def _on_tool_use(self, event: dict) -> None:
        """Handle tool invocation start — flush live text, update status."""
        if self.live_msg:
            chunk_md = self.live_text[self.sent_offset:]
            display_md = clean_file_markers(chunk_md)
            if display_md:
                try:
                    rendered = renderer.render(display_md)
                    await self.live_msg.edit_text(
                        rendered[:TELEGRAM_MAX_LENGTH],
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    )
                except Exception:
                    pass
                self.finalized_msgs.append(self.live_msg)
            else:
                with contextlib.suppress(Exception):
                    await self.live_msg.delete()
            self.sent_offset = len(self.live_text)
            self.live_msg = None
        self._speculative_sent_len = 0
        if self.show_tools:
            if self.current_active:
                self.finished_lines.append(finished_line(self.current_active))
            await self._update_status(event["status"])

    async def _on_tool_result(self, event: dict) -> None:
        """Handle tool completion — update status display."""
        if self.show_tools and self.current_active:
            self.finished_lines.append(finished_line(self.current_active))
            await self._update_status("")

    async def _on_partial(self, event: dict) -> None:
        """Handle streaming text delta."""
        self.live_text += event["text"]
        try:
            await self._update_live(self.live_text)
        except Exception:
            logger.exception("_update_live error")

    def _on_result(self, event: dict) -> None:
        """Handle final result with usage metadata."""
        from bot.sessions import set_usage

        self.response_text = event.get("text", "")
        usage_data = {
            k: event.get(k)
            for k in ("usage", "cost", "num_turns", "duration_ms", "duration_api_ms")
            if event.get(k) is not None
        }
        if usage_data:
            set_usage(
                self.chat_id, self.thread_id,
                # session_user_id is needed — caller must set it; we use chat_id's
                # thread context. But set_usage is called with the same args as the
                # outer function, so we store session_user_id on the instance.
                getattr(self, 'session_user_id', 0),
                usage_data,
            )

    # ------------------------------------------------------------------
    # Status message (tool progress display)
    # ------------------------------------------------------------------

    async def _update_status(self, new_active: str = "") -> None:
        """Create or update the tool-status message."""
        from bot.config import STATUS_EDIT_INTERVAL

        self.current_active = new_active
        lines = list(self.finished_lines)
        if self.current_active:
            lines.append(self.current_active)
        if not lines:
            return

        text = "\n".join(lines)

        now = asyncio.get_event_loop().time()
        if self.status_msg and (now - self.last_edit_time) < STATUS_EDIT_INTERVAL:
            return

        try:
            if self.status_msg is None:
                self.status_msg = await self._send_new_message(text)
            else:
                await self.status_msg.edit_text(text)
            self.last_edit_time = asyncio.get_event_loop().time()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Live streaming display
    # ------------------------------------------------------------------

    def _check_flood(self, exc: Exception) -> None:
        """If exc is a flood-control error, set backoff deadline."""
        msg = str(exc)
        if "Flood control" not in msg and "Too Many Requests" not in msg:
            return
        m = re.search(r"Retry in (\d+)", msg)
        wait = int(m.group(1)) if m else 30
        self.flood_until = asyncio.get_event_loop().time() + wait
        infra_logger.warning("[STREAM] flood control — backing off %ds", wait)

    async def _update_live(self, text: str) -> None:
        """Update the live-streaming message with accumulated text."""
        now = asyncio.get_event_loop().time()

        # Respect flood control backoff
        if now < self.flood_until:
            return

        chunk_md = text[self.sent_offset:]
        if not chunk_md:
            return

        # Check if current chunk's HTML is approaching the limit
        split_pos = find_overflow_split(chunk_md, renderer)
        if split_pos is not None and self.live_msg:
            # Finalize current message with the portion that fits
            finalize_md = chunk_md[:split_pos].rstrip()
            finalized = False
            try:
                rendered = renderer.render(finalize_md)
                await self.live_msg.edit_text(
                    rendered,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
                finalized = True
            except Exception as e:
                self._check_flood(e)
                if now < self.flood_until:
                    return
                infra_logger.warning("[STREAM] finalize HTML failed: %s", e)
                # HTML failed — try plain text
                try:
                    await self.live_msg.edit_text(finalize_md[:TELEGRAM_MAX_LENGTH])
                    finalized = True
                except Exception as e2:
                    self._check_flood(e2)
                    if now < self.flood_until:
                        return
                    infra_logger.warning("[STREAM] finalize plain failed: %s", e2)
            if finalized:
                self.finalized_msgs.append(self.live_msg)
                self._speculative.append(self.live_msg)
                self.sent_offset += split_pos
                self.live_msg = None
                self.last_live_edit = 0
                chunk_md = text[self.sent_offset:]
            # If finalization failed, skip — will retry on next partial

        # Throttle display updates (but not overflow checks above)
        if self.live_msg and (now - self.last_live_edit) < LIVE_EDIT_INTERVAL:
            return

        display = chunk_md[:TELEGRAM_MAX_LENGTH - 20] + " \u270d\ufe0f" if chunk_md else ""
        if not display:
            return

        try:
            if self.live_msg is None:
                self.live_msg = await self._send_new_message(display)
                # Persist live message ID for restart recovery
                from bot.streams import set_stream_live_message_id
                set_stream_live_message_id(
                    self.chat_id, self.thread_id,
                    getattr(self, 'session_user_id', 0),
                    self.live_msg.message_id,
                )
            else:
                await self.live_msg.edit_text(display)
            self.last_live_edit = asyncio.get_event_loop().time()
        except Exception as e:
            self._check_flood(e)
            if now >= self.flood_until:
                infra_logger.warning("[STREAM] live update failed: %s", e)

    async def flush_live(self) -> None:
        """Final flush of any buffered live text."""
        if self.live_text:
            await self._update_live(self.live_text)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup_on_stop(self) -> None:
        """Delete all messages when generation was stopped/cancelled."""
        if self.status_msg:
            with contextlib.suppress(Exception):
                await self.status_msg.delete()
        for fm in self.finalized_msgs:
            with contextlib.suppress(Exception):
                await fm.delete()
        if self.live_msg:
            with contextlib.suppress(Exception):
                await self.live_msg.delete()

    async def cleanup_status(self) -> None:
        """Delete the tool-status message (always runs in finally)."""
        if self.status_msg:
            with contextlib.suppress(Exception):
                await self.status_msg.delete()

    async def delete_speculative_messages(self) -> None:
        """Delete speculative messages (used on silent/empty result)."""
        for msg in self._speculative:
            with contextlib.suppress(Exception):
                await msg.delete()
        if self.live_msg:
            with contextlib.suppress(Exception):
                await self.live_msg.delete()

    # ------------------------------------------------------------------
    # Sending helpers (work in both update and bot-only modes)
    # ------------------------------------------------------------------

    async def _send_rendered(self, text: str) -> None:
        """Send rendered markdown text, using the appropriate sender mode."""
        if self.update is not None:
            from bot.telegram_sender import send_rendered
            await send_rendered(self.update, text, self.context)
        else:
            from bot.telegram_sender import send_rendered_bot
            await send_rendered_bot(self._bot, self.chat_id, text, self.tg_thread_id)

    async def _send_rendered_collect(self, text: str) -> list:
        """Send rendered markdown text and return sent messages."""
        if self.update is not None:
            from bot.telegram_sender import send_rendered_collect
            return await send_rendered_collect(
                self.update, text, self.context, self.tg_thread_id,
            )
        from bot.telegram_sender import send_rendered_collect_bot
        return await send_rendered_collect_bot(
            self._bot, self.chat_id, text, self.tg_thread_id,
        )

    async def finalize_response(self) -> None:
        """Process and send the final response text.

        Handles the full post-streaming flow: deleting intermediates,
        editing/sending final text, sending files and images.
        """
        from bot.attachments import extract_image_urls, split_file_segments
        from bot.telegram_sender import send_file_group
        from bot.types import FileSegment
        from bot.workspaces import ensure_workspace

        # 1. Process result
        if self.response_text is None:
            self.response_text = "Claude processed the request but returned no text output."

        if not self.response_text:
            # Silent exit — clean up speculative and live_msg too
            await self.delete_speculative_messages()
            return

        response_text, image_urls = extract_image_urls(self.response_text)
        workspace_path = str(ensure_workspace(self.chat_id))
        segments = split_file_segments(response_text, workspace_path)
        file_segments = [s for s in segments if isinstance(s, FileSegment)]
        cleaned_response = clean_file_markers(response_text)

        # effective_offset: how much of response_text was already shown
        effective_offset = max(self.sent_offset, self._speculative_sent_len)
        if cleaned_response:
            remaining = cleaned_response[min(effective_offset, len(cleaned_response)):]
        else:
            remaining = ""

        # Guard: if streaming was active (live_text populated) and we already
        # finalized messages, the content was shown to the user via live
        # message editing — don't send a duplicate text message.
        # Files, images, and LaTeX are still sent normally below.
        if self.finalized_msgs and self.live_text:
            remaining = ""

        if not remaining and not image_urls and not file_segments:
            # Everything already displayed — just finalize live_msg if needed
            if self.live_msg:
                chunk_md = clean_file_markers(self.live_text[self.sent_offset:])
                if chunk_md:
                    try:
                        rendered = renderer.render(chunk_md)
                        await self.live_msg.edit_text(
                            rendered[:TELEGRAM_MAX_LENGTH],
                            parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True,
                        )
                    except Exception:
                        pass
                else:
                    with contextlib.suppress(Exception):
                        await self.live_msg.delete()
        else:
            if self.live_msg:
                display_md = clean_file_markers(self.live_text[self.sent_offset:])
                if display_md and remaining:
                    try:
                        rendered = renderer.render(remaining)
                        if len(rendered) <= TELEGRAM_MAX_LENGTH:
                            await self.live_msg.edit_text(
                                rendered,
                                parse_mode=ParseMode.HTML,
                                disable_web_page_preview=True,
                            )
                        else:
                            await self.live_msg.delete()
                            await self._send_rendered(remaining)
                    except Exception:
                        with contextlib.suppress(Exception):
                            await self.live_msg.delete()
                        if remaining:
                            await self._send_rendered(remaining)
                else:
                    with contextlib.suppress(Exception):
                        await self.live_msg.delete()
                    if remaining:
                        await self._send_rendered(remaining)
            elif remaining:
                await self._send_rendered(remaining)

        # Send file attachments
        for seg in file_segments:
            try:
                await send_file_group(
                    self._bot, self.chat_id, seg.files, self.tg_thread_id,
                )
            except Exception as e:
                logger.warning("Failed to send file group: %s", e)

        # Send image URLs
        for img_url in image_urls:
            try:
                await self._bot.send_photo(
                    chat_id=self.chat_id,
                    photo=img_url,
                    message_thread_id=self.tg_thread_id,
                )
            except Exception:
                logger.warning("Failed to send photo URL: %s", img_url)

        # Send LaTeX rendered images (grouped as album when multiple)
        from bot.latex_render import extract_latex_blocks, render_all_latex
        if response_text:
            latex_blocks = extract_latex_blocks(response_text)
            if latex_blocks:
                import functools
                import tempfile
                loop = asyncio.get_event_loop()
                with tempfile.TemporaryDirectory() as tmpdir:
                    png_paths = await loop.run_in_executor(
                        None, functools.partial(render_all_latex, response_text, tmpdir)
                    )
                    if len(png_paths) >= 2:
                        # Send as a media group (album)
                        from telegram import InputMediaPhoto
                        try:
                            media = []
                            open_files = []
                            for png_path in png_paths:
                                f = open(png_path, 'rb')  # noqa: SIM115
                                open_files.append(f)
                                media.append(InputMediaPhoto(media=f))
                            await self._bot.send_media_group(
                                chat_id=self.chat_id,
                                media=media,
                                message_thread_id=self.tg_thread_id,
                            )
                        except Exception:
                            logger.warning(
                                "Failed to send LaTeX album,"
                                " falling back to individual photos",
                            )
                            for png_path in png_paths:
                                try:
                                    with open(png_path, 'rb') as f:
                                        await self._bot.send_photo(
                                            chat_id=self.chat_id,
                                            photo=f,
                                            message_thread_id=self.tg_thread_id,
                                        )
                                except Exception:
                                    logger.warning("Failed to send LaTeX image: %s", png_path)
                        finally:
                            for f in open_files:
                                with contextlib.suppress(Exception):
                                    f.close()
                    elif len(png_paths) == 1:
                        # Single image — send as regular photo
                        try:
                            with open(png_paths[0], 'rb') as f:
                                await self._bot.send_photo(
                                    chat_id=self.chat_id,
                                    photo=f,
                                    message_thread_id=self.tg_thread_id,
                                )
                        except Exception:
                            logger.warning("Failed to send LaTeX image: %s", png_paths[0])
