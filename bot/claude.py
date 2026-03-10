"""Claude integration — unified streaming entry point.

``stream_claude()`` is the single public API.  It handles all shared
setup (workspace logger, active-stream tracking, restart-context
breadcrumbs, preamble construction) and teardown, then delegates the
transport-specific work to a backend in ``bot.backends``.
"""

import asyncio
import logging

from bot.backends import HAS_SDK, stream_sdk, stream_subprocess
from bot.config import ADMIN_USER_ID, WORKING_DIR
from bot.formatting import finished_line, format_tool_status  # noqa: F401
from bot.logging_setup import get_workspace_logger

# Re-export from modules for backward compatibility
from bot.process import _active_procs, kill_active_proc  # noqa: F401
from bot.prompts import (
    _append_restart_context,
    _build_preamble,
    _clear_restart_context,
    _read_restart_context,
    _restart_context_path,
)
from bot.sessions import get_session_id, set_session_id
from bot.streams import add_active_stream, remove_active_stream, set_stream_session_id

logger = logging.getLogger(__name__)

# Re-export prompt helpers so existing ``from bot.claude import …`` still works
_restart_context_path = _restart_context_path  # noqa: F841
_append_restart_context = _append_restart_context  # noqa: F841
_clear_restart_context = _clear_restart_context  # noqa: F841
_read_restart_context = _read_restart_context  # noqa: F841
_build_preamble = _build_preamble  # noqa: F841


async def stream_claude(message: str, chat_id: int, thread_id: int, user_id: int,
                        working_dir: str | None = None, verbose: bool = False,
                        stop_event: asyncio.Event | None = None,
                        real_user_id: int | None = None):
    """Stream Claude output and yield events as they arrive.

    Yields dicts with keys:
      - {"type": "tool_use", "status": "..."}
      - {"type": "tool_result"}
      - {"type": "partial", "text": "..."} (only when verbose=True)
      - {"type": "result", "text": "...", "session_id": "..."}
      - {"type": "error", "text": "..."}
      - {"type": "stopped"}  (generation cancelled via /stop)

    Shared setup and teardown are handled here; the transport-specific
    streaming is delegated to ``stream_sdk`` or ``stream_subprocess``
    from ``bot.backends``.
    """
    # ── Shared setup ─────────────────────────────────────────────
    cwd = working_dir or WORKING_DIR
    sid = get_session_id(chat_id, thread_id, user_id)
    ws_log = get_workspace_logger(chat_id)
    backend_name = "SDK" if HAS_SDK else "subprocess"
    ws_log.info("Claude invocation (%s) — user=%d, session=%s", backend_name, user_id, sid or "new")

    add_active_stream(chat_id, thread_id, user_id, user_message=message[:300])
    if sid:
        set_stream_session_id(chat_id, thread_id, user_id, sid)

    # Restart context breadcrumbs
    _clear_restart_context(chat_id)
    _append_restart_context(chat_id, f"User message: {message[:200]}")

    try:
        is_admin = ADMIN_USER_ID and (real_user_id or user_id) == ADMIN_USER_ID

        preamble = _build_preamble(is_admin, sid)
        if preamble:
            message = preamble + message

        # ── Select and run backend ───────────────────────────────
        backend = stream_sdk if HAS_SDK else stream_subprocess

        async for event in backend(
            message, chat_id, thread_id, user_id,
            is_admin=is_admin,
            cwd=cwd,
            sid=sid,
            verbose=verbose,
            stop_event=stop_event,
            ws_log=ws_log,
            set_session_id_fn=set_session_id,
        ):
            yield event

    except FileNotFoundError as e:
        logger.exception("FileNotFoundError in stream_claude: %s", e)
        yield {
            "type": "error",
            "text": "Error: Claude CLI not found. "
                    "Make sure 'claude' is installed and available in PATH.",
        }
    except Exception as e:
        logger.exception("Unexpected error in stream_claude")
        yield {"type": "error", "text": f"Unexpected error: {e}"}
    finally:
        remove_active_stream(chat_id, thread_id, user_id)
