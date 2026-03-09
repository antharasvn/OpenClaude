"""Repository implementations for the hexagonal architecture.

Production:
  - ``JsonFileSessionRepository`` — wraps ``FileBackedCache`` for sessions
  - ``JsonFileStreamTracker`` — wraps ``FileBackedCache`` for streams

Testing:
  - ``InMemorySessionRepository`` — simple dict-backed implementation
  - ``InMemoryStreamTracker`` — simple dict-backed implementation
"""

from __future__ import annotations

import copy
from typing import Any

from bot.cache import FileBackedCache

# ── Production implementations (file-backed) ─────────────────────────


class JsonFileSessionRepository:
    """Session repository backed by a FileBackedCache (JSON file).

    This wraps the existing FileBackedCache to satisfy the SessionRepository
    protocol.  The underlying cache handles lazy loading, write-behind
    debounce, and atomic file writes.
    """

    def __init__(self, cache: FileBackedCache) -> None:
        self._cache = cache

    def get(self, key: str) -> dict[str, Any] | None:
        return self._cache.get(key)

    def set(self, key: str, value: dict[str, Any]) -> None:
        self._cache.set(key, value)

    def delete(self, key: str) -> bool:
        return self._cache.delete(key)

    def all(self) -> dict[str, Any]:
        return self._cache.all()

    def replace_all(self, data: dict[str, Any]) -> None:
        self._cache.replace_all(data)

    def flush_sync(self) -> None:
        """Delegate flush to the underlying cache."""
        self._cache.flush_sync()

    def reset(self) -> None:
        """Reset in-memory state (for tests)."""
        self._cache.reset()


class JsonFileStreamTracker:
    """Stream tracker backed by a FileBackedCache (JSON file).

    Wraps the existing FileBackedCache to satisfy the StreamTracker protocol.
    """

    def __init__(self, cache: FileBackedCache) -> None:
        self._cache = cache

    def add(self, key: str, entry: dict[str, Any]) -> None:
        self._cache.set(key, entry)
        self._cache.flush_now()

    def get(self, key: str) -> dict[str, Any] | None:
        return self._cache.get(key)

    def update(self, key: str, updates: dict[str, Any]) -> None:
        entry = self._cache.get(key)
        if entry is not None:
            entry.update(updates)
            self._cache.set(key, entry)
            self._cache.flush_now()

    def remove(self, key: str) -> None:
        self._cache.delete(key)
        self._cache.maybe_flush()

    def all(self) -> dict[str, Any]:
        return self._cache.all()

    def flush_sync(self) -> None:
        """Delegate flush to the underlying cache."""
        self._cache.flush_sync()

    def start_flusher(self) -> None:
        """Start periodic background flush."""
        self._cache.start_flusher()

    async def stop_flusher(self) -> None:
        """Stop flusher and do final flush."""
        await self._cache.stop_flusher()

    def reset(self) -> None:
        """Reset in-memory state (for tests)."""
        self._cache.reset()


# ── Test implementations (in-memory) ─────────────────────────────────


class InMemorySessionRepository:
    """In-memory session repository for testing.

    No file I/O, no async — pure dict operations.
    Drop-in replacement for JsonFileSessionRepository in tests.
    """

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = copy.deepcopy(initial) if initial else {}

    def get(self, key: str) -> dict[str, Any] | None:
        val = self._data.get(key)
        return copy.deepcopy(val) if val is not None else None

    def set(self, key: str, value: dict[str, Any]) -> None:
        self._data[key] = copy.deepcopy(value)

    def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    def all(self) -> dict[str, Any]:
        return self._data

    def replace_all(self, data: dict[str, Any]) -> None:
        self._data = copy.deepcopy(data)


class InMemoryStreamTracker:
    """In-memory stream tracker for testing.

    No file I/O, no async — pure dict operations.
    Drop-in replacement for JsonFileStreamTracker in tests.
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def add(self, key: str, entry: dict[str, Any]) -> None:
        self._data[key] = copy.deepcopy(entry)

    def get(self, key: str) -> dict[str, Any] | None:
        val = self._data.get(key)
        return copy.deepcopy(val) if val is not None else None

    def update(self, key: str, updates: dict[str, Any]) -> None:
        if key in self._data:
            self._data[key].update(updates)

    def remove(self, key: str) -> None:
        self._data.pop(key, None)

    def all(self) -> dict[str, Any]:
        return self._data
