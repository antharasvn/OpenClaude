"""Restart recovery — resume interrupted sessions after bot restart."""

import asyncio
import contextlib
import json
import logging
import re
from typing import Any

from bot.config import ACTIVE_STREAMS_FILE, RESTART_MESSAGES_FILE, RESTART_STATE_FILE
from bot.logging_setup import infra_logger
from bot.prompts import _get_current_commit, _read_restart_commit, _read_restart_context
from bot.renderer import TelegramRenderer, split_message
from bot.sessions import get_session_id
from bot.workspaces import get_working_dir

logger = logging.getLogger(__name__)

RESUME_TIMEOUT = 120  # seconds — kill resume if it takes longer


class RestartRecoveryService:
    """Handles resuming interrupted sessions after a bot restart."""

    def __init__(
        self,
        bot: Any,
        renderer: TelegramRenderer,
        stream_fn: Any,
        settings: dict[str, Any] | None = None,
    ) -> None:
        self._bot = bot
        self._renderer = renderer
        self._stream_fn = stream_fn  # bot.claude.stream_claude
        self._settings = settings or {}

    async def recover_interrupted_sessions(self) -> None:
        """Edit restart messages and resume all interrupted generations."""
        await self._edit_restart_messages()
        interrupted = self._collect_interrupted()
        if not interrupted:
            return

        infra_logger.info("Resuming %d interrupted generation(s)", len(interrupted))

        async def _run_resumes() -> None:
            await asyncio.gather(
                *[self._resume_with_timeout(e) for e in interrupted.values()]
            )
            infra_logger.info("Restart recovery complete")

        asyncio.create_task(_run_resumes())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _edit_restart_messages(self) -> None:
        """Edit 'Restarting...' messages to show success."""
        if not RESTART_MESSAGES_FILE.exists():
            return
        try:
            msgs = json.loads(RESTART_MESSAGES_FILE.read_text())
            for entry in msgs:
                try:
                    await self._bot.edit_message_text(
                        chat_id=entry["chat_id"],
                        message_id=entry["message_id"],
                        text="\u2705 Restart complete",
                    )
                except Exception as e:
                    infra_logger.warning(
                        "Failed to edit restart message %s in chat %s: %s",
                        entry.get("message_id"),
                        entry.get("chat_id"),
                        e,
                    )
        except (json.JSONDecodeError, OSError) as e:
            infra_logger.warning("Failed to read restart messages file: %s", e)
        finally:
            RESTART_MESSAGES_FILE.unlink(missing_ok=True)

    @staticmethod
    def _collect_interrupted() -> dict[str, dict]:
        """Collect interrupted chats from restart state and active streams files."""
        interrupted: dict[str, dict] = {}
        for state_file in (RESTART_STATE_FILE, ACTIVE_STREAMS_FILE):
            if not state_file.exists():
                continue
            try:
                data = json.loads(state_file.read_text())
                interrupted.update(data)
            except (json.JSONDecodeError, OSError):
                pass
            finally:
                state_file.unlink(missing_ok=True)
        return interrupted

    async def _resume_chat(self, entry: dict) -> None:
        """Resume a single interrupted chat session."""
        cid = entry["chat_id"]
        tid = entry["thread_id"]
        uid = entry["user_id"]
        # Group chats use uid=0 for shared sessions (same as handlers.py)
        session_uid = 0 if cid < 0 else uid
        tg_thread_id = tid or None
        try:
            session_id = get_session_id(cid, tid, session_uid)
            if not session_id:
                # Fallback: session_id stored directly in the stream entry
                session_id = entry.get("session_id")
                if session_id:
                    infra_logger.info(
                        "Session recovered from stream entry for chat=%d thread=%d user=%d: %s",
                        cid, tid, uid, session_id,
                    )
                    # Persist it to sessions cache so stream_claude can find it
                    from bot.sessions import set_session_id as _set_sid

                    _set_sid(cid, tid, session_uid, session_id)
            if not session_id:
                infra_logger.warning(
                    "No session for chat=%d thread=%d user=%d, skipping resume",
                    cid, tid, uid,
                )
                # Still notify the user
                with contextlib.suppress(Exception):
                    await self._bot.send_message(
                        chat_id=cid,
                        text=(
                            "\u26a0\ufe0f Bot restarted \u2014 no session to resume."
                            " Send a new message to continue."
                        ),
                        message_thread_id=tg_thread_id,
                    )
                return

            resume_msg = self._build_resume_message(cid, entry)
            chat_working_dir = get_working_dir(cid)
            result_text = None
            stop_event = asyncio.Event()
            async for event in self._stream_fn(
                resume_msg,
                cid,
                tid,
                session_uid,
                working_dir=chat_working_dir,
                stop_event=stop_event,
                real_user_id=uid,
            ):
                if event.get("type") == "result" or event.get("type") == "error":
                    result_text = event.get("text", "")

            if result_text:
                await self._send_result(cid, tg_thread_id, result_text)

            infra_logger.info("Resumed chat=%d thread=%d user=%d", cid, tid, uid)
        except Exception as e:
            infra_logger.error(
                "Failed to resume chat=%d thread=%d user=%d: %s", cid, tid, uid, e
            )
            with contextlib.suppress(Exception):
                await self._bot.send_message(
                    chat_id=cid,
                    text=(
                        "\u26a0\ufe0f Bot restarted \u2014 couldn't resume your"
                        " previous task. Send a new message to continue."
                    ),
                    message_thread_id=tg_thread_id,
                )

    @staticmethod
    def _build_git_state(cid: int) -> str:
        """Build a git state line for the resume message."""
        old_commit = _read_restart_commit(cid)
        current_commit = _get_current_commit()
        if not old_commit or old_commit == "unknown":
            return f"Git state: now on {current_commit}."
        if old_commit == current_commit:
            return f"Git state: commit {current_commit} (unchanged)."
        return (
            f"Git state: was on {old_commit}, now on {current_commit} "
            "(ROLLBACK OCCURRED — a bad commit was reverted by safe-restart)."
        )

    @staticmethod
    def _build_resume_message(cid: int, entry: dict) -> str:
        """Build the system message used to prompt Claude to resume."""
        git_state = RestartRecoveryService._build_git_state(cid)
        restart_ctx = _read_restart_context(cid)

        if restart_ctx:
            return (
                "[System: The bot restarted mid-generation.\n\n"
                f"{git_state}\n\n"
                f"What you were doing:\n{restart_ctx}\n\n"
                "The restart was likely triggered by the safe-restart hook "
                "(which rolls back failed commits if needed).\n\n"
                "Briefly tell the user: the bot restarted, "
                "whether a rollback happened, and what you were doing. "
                "Then immediately continue or redo the task. "
                "Do not wait for confirmation.]"
            )
        user_msg_hint = entry.get("user_message", "")
        if user_msg_hint:
            return (
                "[System: The bot restarted mid-generation.\n\n"
                f"{git_state}\n\n"
                f'The user\'s message was: "{user_msg_hint}".\n\n'
                "Briefly notify the user that you restarted and are continuing, "
                "then immediately resume and complete the task without waiting "
                "for confirmation.]"
            )
        return (
            "[System: The bot restarted mid-generation.\n\n"
            f"{git_state}\n\n"
            "Briefly notify the user that you restarted and "
            "are continuing, then resume the task without waiting for "
            "confirmation.]"
        )

    async def _send_result(
        self, chat_id: int, thread_id: int | None, result_text: str
    ) -> None:
        """Send the resume result to the user, with HTML fallback."""
        md_chunks = split_message(result_text)
        for md_chunk in md_chunks:
            rendered = self._renderer.render(md_chunk)
            try:
                await self._bot.send_message(
                    chat_id=chat_id,
                    text=rendered,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    message_thread_id=thread_id,
                )
            except Exception:
                plain = re.sub(r"<[^>]+>", "", rendered)
                for pc in split_message(plain):
                    await self._bot.send_message(
                        chat_id=chat_id,
                        text=pc,
                        message_thread_id=thread_id,
                    )

    async def _resume_with_timeout(self, entry: dict) -> None:
        """Resume a chat with a timeout guard."""
        try:
            await asyncio.wait_for(
                self._resume_chat(entry), timeout=RESUME_TIMEOUT
            )
        except TimeoutError:
            cid = entry["chat_id"]
            tid = entry["thread_id"]
            uid = entry["user_id"]
            infra_logger.error(
                "Resume timed out after %ds for chat=%d thread=%d user=%d",
                RESUME_TIMEOUT, cid, tid, uid,
            )
            with contextlib.suppress(Exception):
                await self._bot.send_message(
                    chat_id=cid,
                    text=(
                        "\u26a0\ufe0f Bot restarted \u2014 resume timed out."
                        " Send a new message to continue."
                    ),
                    message_thread_id=tid or None,
                )
