"""Domain value objects — framework-independent data structures.

These models represent the core domain concepts of the bot, independent
of any specific storage mechanism or messaging framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class UserMessage:
    """A message from a user to the AI assistant."""

    text: str
    chat_id: int
    thread_id: int
    user_id: int
    is_admin: bool = False
    attachments: list[str] = field(default_factory=list)

    @property
    def session_key(self) -> str:
        """Composite key: chat_id:thread_id:user_id."""
        return f"{self.chat_id}:{self.thread_id}:{self.user_id}"


@dataclass
class ChatSession:
    """Persistent session state for a chat/thread/user combination.

    Maps to a single entry in the session store.
    """

    key: str  # "chat_id:thread_id:user_id"
    session_id: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for JSON storage."""
        d: dict[str, Any] = {}
        if self.session_id is not None:
            d["session_id"] = self.session_id
        if self.updated_at is not None:
            d["updated_at"] = self.updated_at
        return d

    @classmethod
    def from_dict(cls, key: str, data: dict[str, Any]) -> ChatSession:
        """Deserialize from a stored dict."""
        return cls(
            key=key,
            session_id=data.get("session_id"),
            updated_at=data.get("updated_at"),
        )

    def touch(self) -> None:
        """Update the timestamp to now."""
        self.updated_at = datetime.now().isoformat()


@dataclass
class StreamState:
    """Transient state for an active streaming response.

    Tracked for crash recovery: if the bot restarts mid-stream,
    the recovery service uses this to resume or notify the user.
    """

    key: str  # "chat_id:thread_id:user_id"
    chat_id: int
    thread_id: int
    user_id: int
    session_id: str | None = None
    user_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for JSON storage."""
        d: dict[str, Any] = {
            "chat_id": self.chat_id,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
        }
        if self.session_id:
            d["session_id"] = self.session_id
        if self.user_message:
            d["user_message"] = self.user_message
        return d

    @classmethod
    def from_dict(cls, key: str, data: dict[str, Any]) -> StreamState:
        """Deserialize from a stored dict."""
        return cls(
            key=key,
            chat_id=data.get("chat_id", 0),
            thread_id=data.get("thread_id", 0),
            user_id=data.get("user_id", 0),
            session_id=data.get("session_id"),
            user_message=data.get("user_message", ""),
        )
