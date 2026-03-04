"""Tests for bot.core.ports — verify protocol conformance."""

from bot.core.ports import SessionRepository, StreamTracker
from bot.core.repositories import (
    InMemorySessionRepository,
    InMemoryStreamTracker,
    JsonFileSessionRepository,
    JsonFileStreamTracker,
)


class TestProtocolConformance:
    """Verify that implementations satisfy their Protocol at runtime."""

    def test_inmemory_session_repo_is_session_repository(self):
        repo = InMemorySessionRepository()
        assert isinstance(repo, SessionRepository)

    def test_inmemory_stream_tracker_is_stream_tracker(self):
        tracker = InMemoryStreamTracker()
        assert isinstance(tracker, StreamTracker)

    def test_json_file_session_repo_is_session_repository(self, tmp_dir):
        from bot.cache import FileBackedCache
        cache = FileBackedCache(tmp_dir / "sessions.json")
        repo = JsonFileSessionRepository(cache)
        assert isinstance(repo, SessionRepository)

    def test_json_file_stream_tracker_is_stream_tracker(self, tmp_dir):
        from bot.cache import FileBackedCache
        cache = FileBackedCache(tmp_dir / "streams.json", mode="periodic")
        tracker = JsonFileStreamTracker(cache)
        assert isinstance(tracker, StreamTracker)
