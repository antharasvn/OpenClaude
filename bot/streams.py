"""Active stream tracking (file-backed for crash recovery)."""

import asyncio
import json
import os
import tempfile

from bot.config import ACTIVE_STREAMS_FILE
from bot.logging_setup import logger
from bot.sessions import session_key


# ---------------------------------------------------------------------------
# In-memory streams cache with periodic flush
# ---------------------------------------------------------------------------

_streams_cache: dict | None = None
_flusher_task: asyncio.Task | None = None
_cache_dirty: bool = False
_FLUSH_INTERVAL = 5.0  # flush to disk every 5 seconds


def _ensure_cache() -> dict:
    """Load streams from disk into cache on first access."""
    global _streams_cache
    if _streams_cache is None:
        if ACTIVE_STREAMS_FILE.exists():
            try:
                _streams_cache = json.loads(ACTIVE_STREAMS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                _streams_cache = {}
        else:
            _streams_cache = {}
    return _streams_cache


def _write_to_disk() -> None:
    """Write the current cache to disk (atomic)."""
    global _cache_dirty
    if _streams_cache is None:
        return
    if not _streams_cache:
        # No active streams — remove file
        ACTIVE_STREAMS_FILE.unlink(missing_ok=True)
        _cache_dirty = False
        return
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=ACTIVE_STREAMS_FILE.parent, suffix=".tmp"
        )
        with os.fdopen(fd, "w") as f:
            json.dump(_streams_cache, f, indent=2)
        os.replace(tmp_path, ACTIVE_STREAMS_FILE)
        _cache_dirty = False
    except OSError as e:
        logger.error("Failed to save active streams: %s", e)


async def _flusher_loop() -> None:
    """Periodically flush dirty cache to disk."""
    try:
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL)
            if _cache_dirty:
                _write_to_disk()
    except asyncio.CancelledError:
        # Final flush on cancellation
        if _cache_dirty:
            _write_to_disk()


def start_streams_flusher() -> None:
    """Start the periodic flush background task. Call from post_init."""
    global _flusher_task
    if _flusher_task is None or _flusher_task.done():
        _flusher_task = asyncio.create_task(_flusher_loop())
        logger.info("Streams flusher task started")


async def stop_streams_flusher() -> None:
    """Stop the flusher task and do a final flush. Call on shutdown."""
    global _flusher_task
    if _flusher_task is not None and not _flusher_task.done():
        _flusher_task.cancel()
        try:
            await _flusher_task
        except asyncio.CancelledError:
            pass
    _flusher_task = None
    # Final synchronous flush
    if _cache_dirty:
        _write_to_disk()


def flush_streams() -> None:
    """Synchronous flush for use in atexit or non-async contexts."""
    if _cache_dirty:
        _write_to_disk()


def save_active_streams(streams: dict) -> None:
    """Update cache (backward-compat entry point)."""
    global _streams_cache, _cache_dirty
    _streams_cache = streams
    _cache_dirty = True


def load_active_streams() -> dict:
    """Read active streams (from cache after first call)."""
    return _ensure_cache()


def add_active_stream(chat_id: int, thread_id: int, user_id: int) -> None:
    """Register a stream start. Survives crashes via periodic flush."""
    global _cache_dirty
    streams = _ensure_cache()
    key = session_key(chat_id, thread_id, user_id)
    streams[key] = {"chat_id": chat_id, "thread_id": thread_id, "user_id": user_id}
    _cache_dirty = True


def remove_active_stream(chat_id: int, thread_id: int, user_id: int) -> None:
    """Remove a completed stream."""
    global _cache_dirty
    streams = _ensure_cache()
    key = session_key(chat_id, thread_id, user_id)
    if key in streams:
        del streams[key]
        _cache_dirty = True
