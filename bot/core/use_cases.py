"""Framework-independent business logic (use cases).

These orchestrate domain operations through ports, without depending on
any specific framework (Telegram, asyncio event loops, file I/O, etc.).

This is the starting point — additional use cases will be added as the
hexagonal migration progresses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bot.core.models import ChatSession, StreamState, UserMessage
from bot.core.ports import SessionRepository, StreamTracker


class SessionService:
    """Manages chat session lifecycle through a SessionRepository port."""

    def __init__(self, repo: SessionRepository) -> None:
        self._repo = repo

    def get_session(self, msg: UserMessage) -> ChatSession:
        """Get or create a ChatSession for the given user message."""
        key = msg.session_key
        data = self._repo.get(key)
        if data is not None:
            return ChatSession.from_dict(key, data)
        return ChatSession(key=key)

    def get_session_id(self, chat_id: int, thread_id: int, user_id: int) -> str | None:
        """Get the Claude session ID for a chat/thread/user, or None."""
        key = f"{chat_id}:{thread_id}:{user_id}"
        data = self._repo.get(key)
        if isinstance(data, dict):
            return data.get("session_id")
        return None

    def set_session_id(
        self, chat_id: int, thread_id: int, user_id: int, session_id: str
    ) -> None:
        """Store a Claude session ID."""
        key = f"{chat_id}:{thread_id}:{user_id}"
        existing = self._repo.get(key) or {}
        existing["session_id"] = session_id
        existing["updated_at"] = datetime.now().isoformat()
        self._repo.set(key, existing)

    def clear_session(self, chat_id: int, thread_id: int, user_id: int) -> None:
        """Clear a session, starting fresh."""
        key = f"{chat_id}:{thread_id}:{user_id}"
        self._repo.delete(key)

    def load_all(self) -> dict[str, Any]:
        """Load all sessions (for backward compatibility)."""
        return self._repo.all()

    def save_all(self, data: dict[str, Any]) -> None:
        """Replace all sessions (for backward compatibility)."""
        self._repo.replace_all(data)


class StreamTrackingService:
    """Manages active stream tracking through a StreamTracker port."""

    def __init__(self, tracker: StreamTracker) -> None:
        self._tracker = tracker

    def start_stream(
        self,
        chat_id: int,
        thread_id: int,
        user_id: int,
        user_message: str = "",
    ) -> StreamState:
        """Register a new active stream."""
        key = f"{chat_id}:{thread_id}:{user_id}"
        state = StreamState(
            key=key,
            chat_id=chat_id,
            thread_id=thread_id,
            user_id=user_id,
            user_message=user_message,
        )
        self._tracker.add(key, state.to_dict())
        return state

    def set_session_id(
        self, chat_id: int, thread_id: int, user_id: int, session_id: str
    ) -> None:
        """Attach a session ID to an active stream (for crash recovery)."""
        key = f"{chat_id}:{thread_id}:{user_id}"
        self._tracker.update(key, {"session_id": session_id})

    def end_stream(self, chat_id: int, thread_id: int, user_id: int) -> None:
        """Mark a stream as completed."""
        key = f"{chat_id}:{thread_id}:{user_id}"
        self._tracker.remove(key)

    def get_active_streams(self) -> dict[str, Any]:
        """Get all active streams (for recovery)."""
        return self._tracker.all()

    def get_stream_session_id(
        self, chat_id: int, thread_id: int, user_id: int
    ) -> str | None:
        """Get session_id from an active stream entry."""
        key = f"{chat_id}:{thread_id}:{user_id}"
        entry = self._tracker.get(key)
        if entry:
            return entry.get("session_id")
        return None
