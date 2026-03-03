"""Active stream tracking (file-backed for crash recovery)."""

import sys

from bot.cache import FileBackedCache
from bot.config import ACTIVE_STREAMS_FILE  # noqa: F811
import logging

logger = logging.getLogger(__name__)
from bot.sessions import session_key

# ---------------------------------------------------------------------------
# In-memory streams cache with periodic flush (backed by FileBackedCache)
# ---------------------------------------------------------------------------

_cache = FileBackedCache(
    lambda: sys.modules[__name__].ACTIVE_STREAMS_FILE,  # type: ignore[arg-type]
    flush_interval=5.0,
    mode="periodic",
    delete_when_empty=True,
)


def _reset_cache() -> None:
    """Reset the in-memory cache. Call between tests."""
    _cache.reset()


def start_streams_flusher() -> None:
    """Start the periodic flush background task. Call from post_init."""
    _cache.start_flusher()
    logger.info("Streams flusher task started")


async def stop_streams_flusher() -> None:
    """Stop the flusher task and do a final flush. Call on shutdown."""
    await _cache.stop_flusher()


def flush_streams() -> None:
    """Synchronous flush for use in atexit or non-async contexts."""
    _cache.flush_sync()


def save_active_streams(streams: dict) -> None:
    """Update cache (backward-compat entry point)."""
    _cache.replace_all(streams)


def load_active_streams() -> dict:
    """Read active streams (from cache after first call)."""
    return _cache.all()


def add_active_stream(chat_id: int, thread_id: int, user_id: int,
                      user_message: str = "") -> None:
    """Register a stream start. Persisted immediately for restart recovery."""
    key = session_key(chat_id, thread_id, user_id)
    entry: dict = {"chat_id": chat_id, "thread_id": thread_id, "user_id": user_id}
    if user_message:
        entry["user_message"] = user_message
    _cache.set(key, entry)
    _cache.flush_now()


def set_stream_session_id(chat_id: int, thread_id: int, user_id: int,
                          session_id: str) -> None:
    """Store session_id directly in the active stream entry for crash recovery."""
    key = session_key(chat_id, thread_id, user_id)
    entry = _cache.get(key)
    if entry is not None:
        entry["session_id"] = session_id
        _cache.set(key, entry)
        _cache.flush_now()


def get_stream_session_id(chat_id: int, thread_id: int, user_id: int) -> str | None:
    """Get session_id from the active stream entry (used during resume)."""
    entry = _cache.get(session_key(chat_id, thread_id, user_id))
    if entry:
        return entry.get("session_id")
    return None


def remove_active_stream(chat_id: int, thread_id: int, user_id: int) -> None:
    """Remove a completed stream."""
    key = session_key(chat_id, thread_id, user_id)
    _cache.delete(key)
    _cache.maybe_flush()
