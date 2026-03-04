"""Tests for bot.core.repositories — repository implementations."""

from bot.core.repositories import (
    InMemorySessionRepository,
    InMemoryStreamTracker,
)


class TestInMemorySessionRepository:
    def test_get_missing_returns_none(self):
        repo = InMemorySessionRepository()
        assert repo.get("missing") is None

    def test_set_and_get(self):
        repo = InMemorySessionRepository()
        repo.set("k1", {"session_id": "abc"})
        assert repo.get("k1") == {"session_id": "abc"}

    def test_get_returns_copy(self):
        repo = InMemorySessionRepository()
        repo.set("k1", {"session_id": "abc"})
        result = repo.get("k1")
        result["session_id"] = "mutated"
        assert repo.get("k1") == {"session_id": "abc"}

    def test_delete_existing(self):
        repo = InMemorySessionRepository()
        repo.set("k1", {"session_id": "abc"})
        assert repo.delete("k1") is True
        assert repo.get("k1") is None

    def test_delete_missing(self):
        repo = InMemorySessionRepository()
        assert repo.delete("missing") is False

    def test_all(self):
        repo = InMemorySessionRepository()
        repo.set("a", {"session_id": "1"})
        repo.set("b", {"session_id": "2"})
        data = repo.all()
        assert len(data) == 2
        assert "a" in data
        assert "b" in data

    def test_replace_all(self):
        repo = InMemorySessionRepository()
        repo.set("old", {"session_id": "x"})
        repo.replace_all({"new": {"session_id": "y"}})
        assert repo.get("old") is None
        assert repo.get("new") == {"session_id": "y"}

    def test_initial_data(self):
        repo = InMemorySessionRepository({"k": {"session_id": "init"}})
        assert repo.get("k") == {"session_id": "init"}

    def test_initial_data_is_copied(self):
        init = {"k": {"session_id": "init"}}
        repo = InMemorySessionRepository(init)
        repo.set("k", {"session_id": "changed"})
        assert init["k"]["session_id"] == "init"


class TestInMemoryStreamTracker:
    def test_add_and_get(self):
        tracker = InMemoryStreamTracker()
        tracker.add("k1", {"chat_id": 1, "user_id": 2})
        result = tracker.get("k1")
        assert result == {"chat_id": 1, "user_id": 2}

    def test_get_missing_returns_none(self):
        tracker = InMemoryStreamTracker()
        assert tracker.get("missing") is None

    def test_get_returns_copy(self):
        tracker = InMemoryStreamTracker()
        tracker.add("k1", {"chat_id": 1})
        result = tracker.get("k1")
        result["chat_id"] = 999
        assert tracker.get("k1") == {"chat_id": 1}

    def test_update(self):
        tracker = InMemoryStreamTracker()
        tracker.add("k1", {"chat_id": 1})
        tracker.update("k1", {"session_id": "sid"})
        result = tracker.get("k1")
        assert result["chat_id"] == 1
        assert result["session_id"] == "sid"

    def test_update_missing_is_noop(self):
        tracker = InMemoryStreamTracker()
        tracker.update("missing", {"session_id": "sid"})
        assert tracker.get("missing") is None

    def test_remove(self):
        tracker = InMemoryStreamTracker()
        tracker.add("k1", {"chat_id": 1})
        tracker.remove("k1")
        assert tracker.get("k1") is None

    def test_remove_missing_is_noop(self):
        tracker = InMemoryStreamTracker()
        tracker.remove("missing")  # should not raise

    def test_all(self):
        tracker = InMemoryStreamTracker()
        tracker.add("a", {"chat_id": 1})
        tracker.add("b", {"chat_id": 2})
        data = tracker.all()
        assert len(data) == 2

    def test_multiple_operations(self):
        tracker = InMemoryStreamTracker()
        tracker.add("k1", {"chat_id": 1})
        tracker.add("k2", {"chat_id": 2})
        tracker.remove("k1")
        assert len(tracker.all()) == 1
        assert tracker.get("k1") is None
        assert tracker.get("k2") is not None
