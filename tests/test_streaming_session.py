"""Tests for StreamingSession (bot/streaming_session.py).

Covers:
- Event dispatch (handle_event routing)
- Partial text accumulation
- Tool use status management
- Result handling
- Error and special event types
- Cleanup methods (stop, status, intermediate, speculative)
- Flood control detection
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.streaming_session import StreamingSession

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_session(streaming=True, show_tools=True):
    """Create a StreamingSession with mocked Telegram objects."""
    update = MagicMock()
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.bot = AsyncMock()

    session = StreamingSession(
        update=update,
        context=context,
        chat_id=123,
        thread_id=0,
        tg_thread_id=None,
        streaming=streaming,
        show_tools=show_tools,
    )
    return session


# ---------------------------------------------------------------------------
# Event dispatch
# ---------------------------------------------------------------------------

class TestEventDispatch:
    @pytest.mark.asyncio
    async def test_partial_event_accumulates_text(self):
        session = _make_session()
        # Prevent actual live update by mocking _update_live
        session._update_live = AsyncMock()

        await session.handle_event({"type": "partial", "text": "Hello "})
        assert session.live_text == "Hello "

        await session.handle_event({"type": "partial", "text": "world"})
        assert session.live_text == "Hello world"

    @pytest.mark.asyncio
    async def test_result_event_sets_response(self):
        session = _make_session()
        with patch("bot.sessions.set_usage"):
            session._on_result({"type": "result", "text": "Final answer", "session_id": "s1"})
        assert session.response_text == "Final answer"

    @pytest.mark.asyncio
    async def test_error_event_sets_response(self):
        session = _make_session()
        await session.handle_event({"type": "error", "text": "Something failed"})
        assert session.response_text == "Something failed"

    @pytest.mark.asyncio
    async def test_silent_event_sets_empty_response(self):
        session = _make_session()
        await session.handle_event({"type": "silent"})
        assert session.response_text == ""

    @pytest.mark.asyncio
    async def test_stopped_event_sets_flag(self):
        session = _make_session()
        await session.handle_event({"type": "stopped"})
        assert session.stopped is True

    @pytest.mark.asyncio
    async def test_unknown_event_type_is_ignored(self):
        session = _make_session()
        # Should not raise
        await session.handle_event({"type": "unknown_type", "data": "whatever"})
        assert session.response_text is None
        assert session.stopped is False


# ---------------------------------------------------------------------------
# Tool use status
# ---------------------------------------------------------------------------

class TestToolUseStatus:
    @pytest.mark.asyncio
    async def test_tool_use_updates_status_when_show_tools(self):
        session = _make_session(show_tools=True)
        session._update_status = AsyncMock()

        await session.handle_event({"type": "tool_use", "status": "Reading file..."})
        session._update_status.assert_called_with("Reading file...")

    @pytest.mark.asyncio
    async def test_tool_use_skips_status_when_not_show_tools(self):
        session = _make_session(show_tools=False)
        session._update_status = AsyncMock()

        await session.handle_event({"type": "tool_use", "status": "Reading file..."})
        session._update_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_tool_use_resets_speculative_sent_len(self):
        session = _make_session(show_tools=False)
        session._speculative_sent_len = 42

        await session.handle_event({"type": "tool_use", "status": "test"})
        assert session._speculative_sent_len == 0

    @pytest.mark.asyncio
    async def test_tool_result_finishes_active_line(self):
        session = _make_session(show_tools=True)
        session.current_active = "Reading file..."
        session._update_status = AsyncMock()

        await session.handle_event({"type": "tool_result"})
        assert len(session.finished_lines) == 1
        session._update_status.assert_called_with("")


# ---------------------------------------------------------------------------
# Result handling
# ---------------------------------------------------------------------------

class TestResultHandling:
    @pytest.mark.asyncio
    async def test_result_saves_usage(self):
        session = _make_session()
        session.session_user_id = 42

        with patch("bot.sessions.set_usage") as mock_usage:
            session._on_result({
                "type": "result",
                "text": "answer",
                "usage": {"input": 100, "output": 50},
                "cost": 0.01,
            })

        mock_usage.assert_called_once()
        assert session.response_text == "answer"

    @pytest.mark.asyncio
    async def test_result_no_usage_when_empty(self):
        session = _make_session()

        with patch("bot.sessions.set_usage") as mock_usage:
            session._on_result({"type": "result", "text": "simple"})

        mock_usage.assert_not_called()
        assert session.response_text == "simple"


# ---------------------------------------------------------------------------
# Cleanup methods
# ---------------------------------------------------------------------------

class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_on_stop_deletes_all_messages(self):
        session = _make_session()
        session.status_msg = AsyncMock()
        session.live_msg = AsyncMock()
        msg1 = AsyncMock()
        msg2 = AsyncMock()
        session.finalized_msgs = [msg1, msg2]

        await session.cleanup_on_stop()

        session.status_msg.delete.assert_called_once()
        session.live_msg.delete.assert_called_once()
        msg1.delete.assert_called_once()
        msg2.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_on_stop_handles_delete_errors(self):
        session = _make_session()
        session.status_msg = AsyncMock()
        session.status_msg.delete.side_effect = Exception("API error")
        session.live_msg = None
        session.finalized_msgs = []

        # Should not raise
        await session.cleanup_on_stop()

    @pytest.mark.asyncio
    async def test_cleanup_status_deletes_status_msg(self):
        session = _make_session()
        session.status_msg = AsyncMock()

        await session.cleanup_status()
        session.status_msg.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_status_noop_when_no_status(self):
        session = _make_session()
        session.status_msg = None
        # Should not raise
        await session.cleanup_status()

    @pytest.mark.asyncio
    async def test_delete_speculative_messages(self):
        session = _make_session()
        msg1 = AsyncMock()
        session._speculative = [msg1]
        session.live_msg = AsyncMock()

        await session.delete_speculative_messages()
        msg1.delete.assert_called_once()
        session.live_msg.delete.assert_called_once()


# ---------------------------------------------------------------------------
# Flood control
# ---------------------------------------------------------------------------

class TestFloodControl:
    def test_check_flood_sets_backoff(self):
        session = _make_session()
        exc = Exception("Flood control exceeded. Retry in 30 seconds.")
        session._check_flood(exc)
        assert session.flood_until > 0

    def test_check_flood_ignores_normal_errors(self):
        session = _make_session()
        exc = Exception("Bad request: message not modified")
        session._check_flood(exc)
        assert session.flood_until == 0

    def test_check_flood_parses_retry_time(self):
        session = _make_session()
        exc = Exception("Flood control exceeded. Retry in 15 seconds.")
        # We need to mock the event loop time
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            session._check_flood(exc)
            assert session.flood_until > 0
        finally:
            loop.close()


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_default_state(self):
        session = _make_session()
        assert session.live_text == ""
        assert session.sent_offset == 0
        assert session.finalized_msgs == []
        assert session._speculative == []
        assert session.response_text is None
        assert session.stopped is False
        assert session.flood_until == 0
        assert session.status_msg is None
        assert session.live_msg is None
        assert session.finished_lines == []
        assert session.current_active == ""
