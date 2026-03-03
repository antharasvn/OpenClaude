"""Generic file-backed cache with write-behind debounce."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Callable, Generic, TypeVar, Union

import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")

PathLike = Union[Path, Callable[[], Path]]


class FileBackedCache(Generic[T]):
    """In-memory dict backed by a JSON file with configurable flush strategy.

    Two flush modes are supported:

    * **debounce** (default) — after each mutation, schedule a write to disk
      after *flush_interval* seconds.  Subsequent mutations reset the timer
      (classic write-behind debounce).  Used by sessions.
    * **periodic** — a long-running asyncio task wakes every *flush_interval*
      seconds and writes if the cache is dirty.  Used by streams.

    Set *mode* to ``"debounce"`` or ``"periodic"`` at construction time.

    *path* can be a ``Path`` or a zero-arg callable returning a ``Path``.
    Using a callable allows test patches on module-level variables to take
    effect at runtime.
    """

    def __init__(
        self,
        path: PathLike,
        flush_interval: float = 1.0,
        *,
        mode: str = "debounce",
        delete_when_empty: bool = False,
    ) -> None:
        self._path_or_fn = path
        self._flush_interval = flush_interval
        self._mode = mode
        self._delete_when_empty = delete_when_empty

        self._data: dict[str, T] | None = None
        self._dirty: bool = False

        # debounce mode
        self._write_behind_handle: asyncio.TimerHandle | None = None

        # periodic mode
        self._flusher_task: asyncio.Task | None = None

    @property
    def _path(self) -> Path:
        """Resolve the file path (supports callable for late binding)."""
        p = self._path_or_fn
        return p() if callable(p) else p

    # ------------------------------------------------------------------
    # Cache access
    # ------------------------------------------------------------------

    def _ensure(self) -> dict[str, T]:
        """Lazy-load from disk on first access."""
        if self._data is None:
            if self._path.exists():
                try:
                    self._data = json.loads(self._path.read_text())
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Failed to load %s: %s", self._path, exc)
                    self._data = {}
            else:
                self._data = {}
        return self._data

    def get(self, key: str) -> T | None:
        return self._ensure().get(key)

    def set(self, key: str, value: T) -> None:
        self._ensure()[key] = value
        self._mark_dirty()

    def delete(self, key: str) -> bool:
        """Remove *key*; return True if it existed."""
        data = self._ensure()
        if key in data:
            del data[key]
            self._mark_dirty()
            return True
        return False

    def all(self) -> dict[str, T]:
        return self._ensure()

    def replace_all(self, data: dict[str, T]) -> None:
        """Wholesale replace the cache contents."""
        self._data = data
        self._mark_dirty()

    # ------------------------------------------------------------------
    # Flush / write-behind
    # ------------------------------------------------------------------

    def _mark_dirty(self) -> None:
        self._dirty = True
        if self._mode == "debounce":
            self._schedule_debounce()
        # periodic mode: the flusher loop picks it up automatically

    def _schedule_debounce(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop (e.g. shutdown) — write immediately
            self._write_to_disk()
            return
        if self._write_behind_handle is not None:
            self._write_behind_handle.cancel()
        self._write_behind_handle = loop.call_later(
            self._flush_interval, self._write_to_disk
        )

    def _write_to_disk(self) -> None:
        if self._data is None:
            return

        if self._delete_when_empty and not self._data:
            self._path.unlink(missing_ok=True)
            self._dirty = False
            return

        payload = json.dumps(self._data, indent=2)
        tmp_path: str | None = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=self._path.parent, suffix=".tmp"
            )
            with os.fdopen(fd, "w") as fh:
                fh.write(payload)
            os.replace(tmp_path, self._path)
            tmp_path = None
            self._dirty = False
        except OSError:
            # Fallback: direct write
            try:
                self._path.write_text(payload)
                self._dirty = False
                logger.warning(
                    "%s: atomic replace failed, used direct write", self._path
                )
            except OSError as exc:
                logger.error("Failed to save %s: %s", self._path, exc)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # -- public flush API ------------------------------------------------

    def flush_sync(self) -> None:
        """Flush to disk immediately (synchronous). For shutdown / atexit."""
        if self._write_behind_handle is not None:
            self._write_behind_handle.cancel()
            self._write_behind_handle = None
        if self._dirty and self._data is not None:
            self._write_to_disk()

    def flush_now(self) -> None:
        """Flush to disk immediately, unconditionally.

        Use for critical data that must be persisted before an external
        process (e.g. restart.sh) might snapshot the file.  Unlike
        ``maybe_flush``, this writes even when a periodic flusher task
        is running.
        """
        if self._dirty and self._data is not None:
            self._write_to_disk()

    def maybe_flush(self) -> None:
        """Flush immediately if no background flusher is running (test helper)."""
        if self._flusher_task is None and self._dirty:
            self._write_to_disk()

    # -- periodic flusher (streams mode) ---------------------------------

    def start_flusher(self) -> None:
        """Start a periodic flush background task."""
        if self._flusher_task is None or self._flusher_task.done():
            self._flusher_task = asyncio.create_task(self._flusher_loop())

    async def stop_flusher(self) -> None:
        """Cancel the flusher task and do a final flush."""
        if self._flusher_task is not None and not self._flusher_task.done():
            self._flusher_task.cancel()
            try:
                await self._flusher_task
            except asyncio.CancelledError:
                pass
        self._flusher_task = None
        if self._dirty:
            self._write_to_disk()

    async def _flusher_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._flush_interval)
                if self._dirty:
                    self._write_to_disk()
        except asyncio.CancelledError:
            if self._dirty:
                self._write_to_disk()

    # -- test helpers ----------------------------------------------------

    def reset(self) -> None:
        """Reset in-memory state. Used by tests."""
        self._data = None
        self._write_behind_handle = None
        self._dirty = False
