"""Session persistence (load/save/clear session IDs)."""

import asyncio
import json
import os
import tempfile
from datetime import datetime

from bot.config import SESSION_FILE
from bot.logging_setup import logger


# ---------------------------------------------------------------------------
# In-memory session cache with write-behind
# ---------------------------------------------------------------------------

_sessions_cache: dict | None = None
_write_behind_handle: asyncio.TimerHandle | None = None
_cache_dirty: bool = False
_WRITE_BEHIND_DELAY = 1.0  # max 1 second debounce


def _reset_cache() -> None:
    """Reset the in-memory session cache. Used by tests."""
    global _sessions_cache, _write_behind_handle, _cache_dirty
    _sessions_cache = None
    _write_behind_handle = None
    _cache_dirty = False


def _ensure_cache() -> dict:
    """Load sessions from disk into cache on first access."""
    global _sessions_cache
    if _sessions_cache is None:
        if SESSION_FILE.exists():
            try:
                _sessions_cache = json.loads(SESSION_FILE.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load sessions: %s", e)
                _sessions_cache = {}
        else:
            _sessions_cache = {}
    return _sessions_cache


def _write_to_disk() -> None:
    """Write the current cache to disk (atomic write with fallback)."""
    global _cache_dirty
    if _sessions_cache is None:
        return
    data = json.dumps(_sessions_cache, indent=2)
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=SESSION_FILE.parent, suffix=".tmp"
        )
        with os.fdopen(fd, "w") as f:
            f.write(data)
        os.replace(tmp_path, SESSION_FILE)
        tmp_path = None
        _cache_dirty = False
    except OSError:
        try:
            SESSION_FILE.write_text(data)
            _cache_dirty = False
            logger.warning("save_sessions: atomic replace failed, used direct write")
        except OSError as e2:
            logger.error("Failed to save sessions: %s", e2)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _schedule_write_behind() -> None:
    """Schedule a write-behind flush, debounced to max once per second."""
    global _write_behind_handle, _cache_dirty
    _cache_dirty = True
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop — write immediately (e.g. during shutdown)
        _write_to_disk()
        return
    if _write_behind_handle is not None:
        _write_behind_handle.cancel()
    _write_behind_handle = loop.call_later(_WRITE_BEHIND_DELAY, _write_to_disk)


def flush_sessions() -> None:
    """Flush cached sessions to disk immediately. Call on clean shutdown."""
    global _write_behind_handle, _cache_dirty
    if _write_behind_handle is not None:
        _write_behind_handle.cancel()
        _write_behind_handle = None
    if _cache_dirty and _sessions_cache is not None:
        _write_to_disk()


def load_sessions() -> dict:
    """Load session mapping (from cache after first call)."""
    return _ensure_cache()


def save_sessions(sessions: dict) -> None:
    """Persist session mapping (write-behind via cache)."""
    global _sessions_cache
    _sessions_cache = sessions
    _schedule_write_behind()


def session_key(chat_id: int, thread_id: int, user_id: int) -> str:
    """Build a composite session key: chat_id:thread_id:user_id."""
    return f"{chat_id}:{thread_id}:{user_id}"


def get_session_id(chat_id: int, thread_id: int, user_id: int) -> str | None:
    """Get the Claude session ID for a given chat/thread/user combination."""
    sessions = _ensure_cache()
    key = session_key(chat_id, thread_id, user_id)
    return sessions.get(key, {}).get("session_id")


def set_session_id(chat_id: int, thread_id: int, user_id: int, sid: str) -> None:
    """Store a Claude session ID for a given chat/thread/user combination."""
    sessions = _ensure_cache()
    key = session_key(chat_id, thread_id, user_id)
    sessions.setdefault(key, {})["session_id"] = sid
    sessions[key]["updated_at"] = datetime.now().isoformat()
    _schedule_write_behind()


def clear_session(chat_id: int, thread_id: int, user_id: int) -> None:
    """Clear the session for a chat/thread/user combination, starting fresh."""
    sessions = _ensure_cache()
    key = session_key(chat_id, thread_id, user_id)
    if key in sessions:
        del sessions[key]
        _schedule_write_behind()
    _usage_cache.pop(key, None)


# ---------------------------------------------------------------------------
# Ephemeral usage cache (lost on restart — that's fine)
# ---------------------------------------------------------------------------

_usage_cache: dict[str, dict] = {}


def set_usage(chat_id: int, thread_id: int, user_id: int, data: dict) -> None:
    """Store usage data for a session."""
    _usage_cache[session_key(chat_id, thread_id, user_id)] = data


def get_usage(chat_id: int, thread_id: int, user_id: int) -> dict | None:
    """Get usage data for a session, or None if not available."""
    return _usage_cache.get(session_key(chat_id, thread_id, user_id))


# ---------------------------------------------------------------------------
# Context percentage helper
# ---------------------------------------------------------------------------

_DEFAULT_CONTEXT_WINDOW = 200_000


def get_context_pct(chat_id: int, thread_id: int, user_id: int) -> tuple[float, int, int] | None:
    """Return (percentage, used_tokens, window_size) or None."""
    data = get_usage(chat_id, thread_id, user_id)
    if not data:
        return None
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    # input_tokens already includes cached tokens; only add cache_creation
    # (tokens written to cache for the first time, not counted in input_tokens)
    used = (
        (usage.get("input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
    )
    if used == 0:
        return None
    window = _DEFAULT_CONTEXT_WINDOW
    pct = used / window if window else 0
    return (pct, used, window)
