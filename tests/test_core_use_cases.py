"""Tests for bot.core.use_cases — business logic orchestration."""

from bot.core.models import UserMessage
from bot.core.repositories import InMemorySessionRepository, InMemoryStreamTracker
from bot.core.use_cases import SessionService, StreamTrackingService


class TestSessionService:
    def _make_service(self, initial=None):
        repo = InMemorySessionRepository(initial)
        return SessionService(repo), repo

    def test_get_session_empty(self):
        svc, _ = self._make_service()
        msg = UserMessage(text="hi", chat_id=1, thread_id=0, user_id=2)
        session = svc.get_session(msg)
        assert session.key == "1:0:2"
        assert session.session_id is None

    def test_get_session_existing(self):
        svc, _ = self._make_service({"1:0:2": {"session_id": "abc"}})
        msg = UserMessage(text="hi", chat_id=1, thread_id=0, user_id=2)
        session = svc.get_session(msg)
        assert session.session_id == "abc"

    def test_set_and_get_session_id(self):
        svc, _ = self._make_service()
        svc.set_session_id(1, 0, 2, "new-sid")
        assert svc.get_session_id(1, 0, 2) == "new-sid"

    def test_get_session_id_missing(self):
        svc, _ = self._make_service()
        assert svc.get_session_id(1, 0, 2) is None

    def test_clear_session(self):
        svc, _ = self._make_service()
        svc.set_session_id(1, 0, 2, "sid")
        svc.clear_session(1, 0, 2)
        assert svc.get_session_id(1, 0, 2) is None

    def test_set_session_id_updates_timestamp(self):
        svc, repo = self._make_service()
        svc.set_session_id(1, 0, 2, "sid")
        data = repo.get("1:0:2")
        assert "updated_at" in data

    def test_load_all(self):
        initial = {"a": {"session_id": "1"}, "b": {"session_id": "2"}}
        svc, _ = self._make_service(initial)
        assert len(svc.load_all()) == 2

    def test_save_all(self):
        svc, repo = self._make_service()
        svc.save_all({"k": {"session_id": "v"}})
        assert repo.get("k") == {"session_id": "v"}


class TestStreamTrackingService:
    def _make_service(self):
        tracker = InMemoryStreamTracker()
        return StreamTrackingService(tracker), tracker

    def test_start_stream(self):
        svc, tracker = self._make_service()
        state = svc.start_stream(1, 0, 2, "hello")
        assert state.key == "1:0:2"
        assert state.user_message == "hello"
        assert tracker.get("1:0:2") is not None

    def test_end_stream(self):
        svc, tracker = self._make_service()
        svc.start_stream(1, 0, 2)
        svc.end_stream(1, 0, 2)
        assert tracker.get("1:0:2") is None

    def test_set_session_id(self):
        svc, tracker = self._make_service()
        svc.start_stream(1, 0, 2)
        svc.set_session_id(1, 0, 2, "sid-123")
        entry = tracker.get("1:0:2")
        assert entry["session_id"] == "sid-123"

    def test_get_stream_session_id(self):
        svc, _ = self._make_service()
        svc.start_stream(1, 0, 2)
        svc.set_session_id(1, 0, 2, "sid-abc")
        assert svc.get_stream_session_id(1, 0, 2) == "sid-abc"

    def test_get_stream_session_id_missing(self):
        svc, _ = self._make_service()
        assert svc.get_stream_session_id(1, 0, 2) is None

    def test_get_active_streams(self):
        svc, _ = self._make_service()
        svc.start_stream(1, 0, 2, "msg1")
        svc.start_stream(3, 0, 4, "msg2")
        streams = svc.get_active_streams()
        assert len(streams) == 2

    def test_multiple_lifecycle(self):
        svc, _ = self._make_service()
        svc.start_stream(1, 0, 2, "msg1")
        svc.start_stream(3, 0, 4, "msg2")
        svc.end_stream(1, 0, 2)
        streams = svc.get_active_streams()
        assert len(streams) == 1
        assert "3:0:4" in streams
