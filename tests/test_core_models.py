"""Tests for bot.core.models — domain value objects."""

from bot.core.models import ChatSession, StreamState, UserMessage


class TestUserMessage:
    def test_session_key(self):
        msg = UserMessage(text="hello", chat_id=123, thread_id=456, user_id=789)
        assert msg.session_key == "123:456:789"

    def test_session_key_zero_thread(self):
        msg = UserMessage(text="hi", chat_id=1, thread_id=0, user_id=2)
        assert msg.session_key == "1:0:2"

    def test_defaults(self):
        msg = UserMessage(text="hi", chat_id=1, thread_id=0, user_id=2)
        assert msg.is_admin is False
        assert msg.attachments == []


class TestChatSession:
    def test_to_dict_full(self):
        s = ChatSession(key="1:0:2", session_id="abc", updated_at="2024-01-01T00:00:00")
        d = s.to_dict()
        assert d == {"session_id": "abc", "updated_at": "2024-01-01T00:00:00"}

    def test_to_dict_empty(self):
        s = ChatSession(key="1:0:2")
        assert s.to_dict() == {}

    def test_from_dict(self):
        data = {"session_id": "xyz", "updated_at": "2024-06-01T12:00:00"}
        s = ChatSession.from_dict("1:0:2", data)
        assert s.key == "1:0:2"
        assert s.session_id == "xyz"
        assert s.updated_at == "2024-06-01T12:00:00"

    def test_from_dict_empty(self):
        s = ChatSession.from_dict("k", {})
        assert s.session_id is None
        assert s.updated_at is None

    def test_roundtrip(self):
        original = ChatSession(key="k", session_id="s1", updated_at="t1")
        restored = ChatSession.from_dict("k", original.to_dict())
        assert restored.key == original.key
        assert restored.session_id == original.session_id
        assert restored.updated_at == original.updated_at

    def test_touch(self):
        s = ChatSession(key="k")
        assert s.updated_at is None
        s.touch()
        assert s.updated_at is not None
        assert "T" in s.updated_at  # ISO format


class TestStreamState:
    def test_to_dict(self):
        state = StreamState(
            key="1:0:2", chat_id=1, thread_id=0, user_id=2,
            session_id="sid", user_message="hello"
        )
        d = state.to_dict()
        assert d["chat_id"] == 1
        assert d["thread_id"] == 0
        assert d["user_id"] == 2
        assert d["session_id"] == "sid"
        assert d["user_message"] == "hello"

    def test_to_dict_minimal(self):
        state = StreamState(key="1:0:2", chat_id=1, thread_id=0, user_id=2)
        d = state.to_dict()
        assert "session_id" not in d
        assert "user_message" not in d

    def test_from_dict(self):
        data = {"chat_id": 5, "thread_id": 3, "user_id": 7,
                "session_id": "s", "user_message": "msg"}
        state = StreamState.from_dict("5:3:7", data)
        assert state.chat_id == 5
        assert state.session_id == "s"
        assert state.user_message == "msg"

    def test_roundtrip(self):
        original = StreamState(
            key="k", chat_id=1, thread_id=2, user_id=3,
            session_id="sid", user_message="hi"
        )
        restored = StreamState.from_dict("k", original.to_dict())
        assert restored.chat_id == original.chat_id
        assert restored.session_id == original.session_id
        assert restored.user_message == original.user_message
