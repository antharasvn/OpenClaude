"""Port definitions (protocols) for the hexagonal architecture.

Ports define the boundaries of the domain core.  Adapters implement
these protocols to connect the core to external systems (Telegram,
file system, Claude API, etc.).

Driving ports (called by external code into the core):
  - Use cases in ``use_cases.py`` serve as driving ports.

Driven ports (called by the core to reach external systems):
  - ``AICompletionPort`` — AI model streaming
  - ``SessionRepository`` — session persistence
  - ``StreamTracker`` — active stream tracking
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

# ── AI Completion Port ────────────────────────────────────────────────

@runtime_checkable
class AICompletionPort(Protocol):
    """Port for streaming AI completions.

    Implementations: SDKBackend, SubprocessBackend (in bot/backends.py).
    """

    async def stream(
        self,
        message: str,
        *,
        chat_id: int,
        thread_id: int,
        user_id: int,
        is_admin: bool,
        cwd: str,
        session_id: str | None,
        verbose: bool,
        stop_event: Any | None,
        ws_log: Any,
        set_session_id_fn: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream AI completion events.

        Yields event dicts compatible with the existing StreamEvent system.
        """
        ...  # pragma: no cover


# ── Session Repository ────────────────────────────────────────────────

@runtime_checkable
class SessionRepository(Protocol):
    """Port for session persistence.

    Implementations:
      - ``JsonFileSessionRepository`` — file-backed (production)
      - ``InMemorySessionRepository`` — dict-backed (tests)
    """

    def get(self, key: str) -> dict[str, Any] | None:
        """Get a session entry by key, or None if not found."""
        ...  # pragma: no cover

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Store a session entry."""
        ...  # pragma: no cover

    def delete(self, key: str) -> bool:
        """Delete a session entry. Returns True if it existed."""
        ...  # pragma: no cover

    def all(self) -> dict[str, Any]:
        """Return all session entries."""
        ...  # pragma: no cover

    def replace_all(self, data: dict[str, Any]) -> None:
        """Replace the entire session store."""
        ...  # pragma: no cover


# ── Stream Tracker ────────────────────────────────────────────────────

@runtime_checkable
class StreamTracker(Protocol):
    """Port for tracking active streams (crash recovery).

    Implementations:
      - ``JsonFileStreamTracker`` — file-backed (production)
      - ``InMemoryStreamTracker`` — dict-backed (tests)
    """

    def add(self, key: str, entry: dict[str, Any]) -> None:
        """Register an active stream."""
        ...  # pragma: no cover

    def get(self, key: str) -> dict[str, Any] | None:
        """Get stream entry, or None."""
        ...  # pragma: no cover

    def update(self, key: str, updates: dict[str, Any]) -> None:
        """Update fields on an existing stream entry."""
        ...  # pragma: no cover

    def remove(self, key: str) -> None:
        """Remove a completed/failed stream."""
        ...  # pragma: no cover

    def all(self) -> dict[str, Any]:
        """Return all active stream entries."""
        ...  # pragma: no cover
