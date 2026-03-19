"""Active stream tracking (file-backed for crash recovery)."""

import logging
import sys

from bot.cache import FileBackedCache
from bot.config import ACTIVE_STREAMS_FILE  # noqa: F401 — kept so patches on the module attr work
from bot.sessions import session_key

logger = logging.getLogger(__name__)

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
    """Store session_id directly in the active stream entry for crash recovery.

    If the stream entry doesn't exist yet (called before add_active_stream),
    a minimal entry is created so the session_id is not silently dropped.
    """
    key = session_key(chat_id, thread_id, user_id)
    entry = _cache.get(key)
    if entry is None:
        logger.warning(
            "set_stream_session_id: no entry for key %s — creating minimal entry",
            key,
        )
        entry = {"chat_id": chat_id, "thread_id": thread_id, "user_id": user_id}
    entry["session_id"] = session_id
    _cache.set(key, entry)
    _cache.flush_now()


def get_stream_session_id(chat_id: int, thread_id: int, user_id: int) -> str | None:
    """Get session_id from the active stream entry (used during resume)."""
    entry = _cache.get(session_key(chat_id, thread_id, user_id))
    if entry:
        return entry.get("session_id")
    return None


def set_stream_live_message_id(chat_id: int, thread_id: int, user_id: int,
                               message_id: int) -> None:
    """Store the live streaming message ID in the active stream entry."""
    key = session_key(chat_id, thread_id, user_id)
    entry = _cache.get(key)
    if isinstance(entry, dict):
        entry["live_message_id"] = message_id
        _cache.set(key, entry)
        _cache.flush_now()


def clear_stream_live_message_id(chat_id: int, thread_id: int, user_id: int) -> None:
    """Remove the live streaming message ID (message was finalized, no longer deletable)."""
    key = session_key(chat_id, thread_id, user_id)
    entry = _cache.get(key)
    if isinstance(entry, dict) and "live_message_id" in entry:
        del entry["live_message_id"]
        _cache.set(key, entry)
        _cache.maybe_flush()


def set_stream_status_msg_id(chat_id: int, thread_id: int, user_id: int,
                              message_id: int) -> None:
    """Store the tool-status message ID in the active stream entry."""
    key = session_key(chat_id, thread_id, user_id)
    entry = _cache.get(key)
    if isinstance(entry, dict):
        entry["status_msg_id"] = message_id
        _cache.set(key, entry)
        _cache.flush_now()


def clear_stream_status_msg_id(chat_id: int, thread_id: int, user_id: int) -> None:
    """Remove the status message ID (message was deleted successfully)."""
    key = session_key(chat_id, thread_id, user_id)
    entry = _cache.get(key)
    if isinstance(entry, dict) and "status_msg_id" in entry:
        del entry["status_msg_id"]
        _cache.set(key, entry)
        _cache.maybe_flush()


def remove_active_stream(chat_id: int, thread_id: int, user_id: int) -> None:
    """Remove a completed stream."""
    key = session_key(chat_id, thread_id, user_id)
    _cache.delete(key)
    _cache.flush_now()
