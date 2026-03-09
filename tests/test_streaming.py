"""Tests for the Claude streaming pipeline (bot/claude.py).

Covers:
- stream_claude() shared setup/teardown
- Event forwarding from backends
- Error handling (FileNotFoundError, generic exceptions)
- Active stream tracking lifecycle
"""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _collect_events(async_gen):
    """Consume an async generator and return a list of yielded items."""
    events = []
    async for event in async_gen:
        events.append(event)
    return events


def _make_fake_backend(*events):
    """Return an async generator function that yields the given events."""
    async def fake_backend(message, chat_id, thread_id, user_id, **kwargs):
        for ev in events:
            yield ev
    return fake_backend


# ---------------------------------------------------------------------------
# stream_claude — event forwarding
# ---------------------------------------------------------------------------

class TestStreamClaude:
    @pytest.mark.asyncio
    async def test_forwards_result_event(self):
        result_event = {"type": "result", "text": "Hello!", "session_id": "s1"}
        backend = _make_fake_backend(result_event)

        with patch("bot.claude.HAS_SDK", True), \
             patch("bot.claude.stream_sdk", backend), \
             patch("bot.claude.get_session_id", return_value=None), \
             patch("bot.claude.get_workspace_logger") as mock_ws_log, \
             patch("bot.claude.add_active_stream"), \
             patch("bot.claude.remove_active_stream"), \
             patch("bot.claude._clear_restart_context"), \
             patch("bot.claude._append_restart_context"), \
             patch("bot.claude._build_preamble", return_value=""), \
             patch("bot.claude.ADMIN_USER_ID", 111111), \
             patch("bot.claude.WORKING_DIR", "/tmp"):
            mock_ws_log.return_value = MagicMock()

            from bot.claude import stream_claude
            events = await _collect_events(
                stream_claude("hi", chat_id=1, thread_id=0, user_id=111111)
            )

        assert len(events) == 1
        assert events[0]["type"] == "result"
        assert events[0]["text"] == "Hello!"

    @pytest.mark.asyncio
    async def test_forwards_multiple_events(self):
        backend = _make_fake_backend(
            {"type": "tool_use", "status": "Reading file..."},
            {"type": "tool_result"},
            {"type": "partial", "text": "chunk"},
            {"type": "result", "text": "Done", "session_id": "s2"},
        )

        with patch("bot.claude.HAS_SDK", True), \
             patch("bot.claude.stream_sdk", backend), \
             patch("bot.claude.get_session_id", return_value="old-session"), \
             patch("bot.claude.get_workspace_logger") as mock_ws_log, \
             patch("bot.claude.add_active_stream"), \
             patch("bot.claude.remove_active_stream"), \
             patch("bot.claude._clear_restart_context"), \
             patch("bot.claude._append_restart_context"), \
             patch("bot.claude._build_preamble", return_value=""), \
             patch("bot.claude.ADMIN_USER_ID", 111111), \
             patch("bot.claude.WORKING_DIR", "/tmp"):
            mock_ws_log.return_value = MagicMock()

            from bot.claude import stream_claude
            events = await _collect_events(
                stream_claude("test", chat_id=1, thread_id=0, user_id=111111)
            )

        assert len(events) == 4
        assert events[0]["type"] == "tool_use"
        assert events[1]["type"] == "tool_result"
        assert events[2]["type"] == "partial"
        assert events[3]["type"] == "result"

    @pytest.mark.asyncio
    async def test_yields_error_on_file_not_found(self):
        async def exploding_backend(message, chat_id, thread_id, user_id, **kwargs):
            raise FileNotFoundError("claude not found")
            yield  # make it an async generator  # noqa: E501

        with patch("bot.claude.HAS_SDK", True), \
             patch("bot.claude.stream_sdk", exploding_backend), \
             patch("bot.claude.get_session_id", return_value=None), \
             patch("bot.claude.get_workspace_logger") as mock_ws_log, \
             patch("bot.claude.add_active_stream"), \
             patch("bot.claude.remove_active_stream"), \
             patch("bot.claude._clear_restart_context"), \
             patch("bot.claude._append_restart_context"), \
             patch("bot.claude._build_preamble", return_value=""), \
             patch("bot.claude.ADMIN_USER_ID", 111111), \
             patch("bot.claude.WORKING_DIR", "/tmp"):
            mock_ws_log.return_value = MagicMock()

            from bot.claude import stream_claude
            events = await _collect_events(
                stream_claude("boom", chat_id=1, thread_id=0, user_id=111111)
            )

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "not found" in events[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_yields_error_on_unexpected_exception(self):
        async def exploding_backend(message, chat_id, thread_id, user_id, **kwargs):
            raise RuntimeError("something broke")
            yield  # noqa: E501

        with patch("bot.claude.HAS_SDK", True), \
             patch("bot.claude.stream_sdk", exploding_backend), \
             patch("bot.claude.get_session_id", return_value=None), \
             patch("bot.claude.get_workspace_logger") as mock_ws_log, \
             patch("bot.claude.add_active_stream"), \
             patch("bot.claude.remove_active_stream"), \
             patch("bot.claude._clear_restart_context"), \
             patch("bot.claude._append_restart_context"), \
             patch("bot.claude._build_preamble", return_value=""), \
             patch("bot.claude.ADMIN_USER_ID", 111111), \
             patch("bot.claude.WORKING_DIR", "/tmp"):
            mock_ws_log.return_value = MagicMock()

            from bot.claude import stream_claude
            events = await _collect_events(
                stream_claude("boom", chat_id=1, thread_id=0, user_id=111111)
            )

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "something broke" in events[0]["text"]

    @pytest.mark.asyncio
    async def test_active_stream_tracking(self):
        backend = _make_fake_backend({"type": "result", "text": "ok", "session_id": None})

        with patch("bot.claude.HAS_SDK", True), \
             patch("bot.claude.stream_sdk", backend), \
             patch("bot.claude.get_session_id", return_value=None), \
             patch("bot.claude.get_workspace_logger") as mock_ws_log, \
             patch("bot.claude.add_active_stream") as mock_add, \
             patch("bot.claude.remove_active_stream") as mock_remove, \
             patch("bot.claude._clear_restart_context"), \
             patch("bot.claude._append_restart_context"), \
             patch("bot.claude._build_preamble", return_value=""), \
             patch("bot.claude.ADMIN_USER_ID", 111111), \
             patch("bot.claude.WORKING_DIR", "/tmp"):
            mock_ws_log.return_value = MagicMock()

            from bot.claude import stream_claude
            await _collect_events(
                stream_claude("track me", chat_id=5, thread_id=2, user_id=111111)
            )

        mock_add.assert_called_once()
        mock_remove.assert_called_once()
        # Both called with the same chat/thread/user
        assert mock_add.call_args[0][:3] == (5, 2, 111111)
        assert mock_remove.call_args[0][:3] == (5, 2, 111111)

    @pytest.mark.asyncio
    async def test_preamble_prepended_to_message(self):
        captured_messages = []

        async def capturing_backend(message, chat_id, thread_id, user_id, **kwargs):
            captured_messages.append(message)
            yield {"type": "result", "text": "ok", "session_id": None}

        with patch("bot.claude.HAS_SDK", True), \
             patch("bot.claude.stream_sdk", capturing_backend), \
             patch("bot.claude.get_session_id", return_value="existing"), \
             patch("bot.claude.get_workspace_logger") as mock_ws_log, \
             patch("bot.claude.add_active_stream"), \
             patch("bot.claude.remove_active_stream"), \
             patch("bot.claude._clear_restart_context"), \
             patch("bot.claude._append_restart_context"), \
             patch("bot.claude._build_preamble", return_value="[PREAMBLE] "), \
             patch("bot.claude.ADMIN_USER_ID", 111111), \
             patch("bot.claude.WORKING_DIR", "/tmp"):
            mock_ws_log.return_value = MagicMock()

            from bot.claude import stream_claude
            await _collect_events(
                stream_claude("hello", chat_id=1, thread_id=0, user_id=111111)
            )

        assert len(captured_messages) == 1
        assert captured_messages[0].startswith("[PREAMBLE] ")
        assert "hello" in captured_messages[0]

    @pytest.mark.asyncio
    async def test_selects_subprocess_backend_when_no_sdk(self):
        backend = _make_fake_backend({"type": "result", "text": "ok", "session_id": None})

        with patch("bot.claude.HAS_SDK", False), \
             patch("bot.claude.stream_subprocess", backend), \
             patch("bot.claude.get_session_id", return_value=None), \
             patch("bot.claude.get_workspace_logger") as mock_ws_log, \
             patch("bot.claude.add_active_stream"), \
             patch("bot.claude.remove_active_stream"), \
             patch("bot.claude._clear_restart_context"), \
             patch("bot.claude._append_restart_context"), \
             patch("bot.claude._build_preamble", return_value=""), \
             patch("bot.claude.ADMIN_USER_ID", 111111), \
             patch("bot.claude.WORKING_DIR", "/tmp"):
            mock_ws_log.return_value = MagicMock()

            from bot.claude import stream_claude
            events = await _collect_events(
                stream_claude("hi", chat_id=1, thread_id=0, user_id=111111)
            )

        assert len(events) == 1
        assert events[0]["type"] == "result"


# ---------------------------------------------------------------------------
# Event types (bot/events.py)
# ---------------------------------------------------------------------------

class TestEventTypes:
    def test_partial_event_defaults(self):
        from bot.events import PartialEvent
        ev = PartialEvent()
        assert ev.type == "partial"
        assert ev.text == ""

    def test_partial_event_with_text(self):
        from bot.events import PartialEvent
        ev = PartialEvent(text="chunk")
        assert ev.text == "chunk"

    def test_result_event_fields(self):
        from bot.events import ResultEvent
        ev = ResultEvent(text="done", session_id="abc", cost=0.05)
        assert ev.type == "result"
        assert ev.text == "done"
        assert ev.session_id == "abc"
        assert ev.cost == 0.05

    def test_tool_use_event(self):
        from bot.events import ToolUseEvent
        ev = ToolUseEvent(status="Reading file.py...")
        assert ev.type == "tool_use"
        assert ev.status == "Reading file.py..."

    def test_error_event(self):
        from bot.events import ErrorEvent
        ev = ErrorEvent(text="oops")
        assert ev.type == "error"
        assert ev.text == "oops"

    def test_stopped_event(self):
        from bot.events import StoppedEvent
        ev = StoppedEvent()
        assert ev.type == "stopped"

    def test_silent_event(self):
        from bot.events import SilentEvent
        ev = SilentEvent()
        assert ev.type == "silent"

    def test_text_block_event(self):
        from bot.events import TextBlockEvent
        ev = TextBlockEvent(text="hello world")
        assert ev.type == "text_block"
        assert ev.text == "hello world"

    def test_tool_result_event(self):
        from bot.events import ToolResultEvent
        ev = ToolResultEvent()
        assert ev.type == "tool_result"


# ---------------------------------------------------------------------------
# Formatting helpers (bot/formatting.py)
# ---------------------------------------------------------------------------

class TestFormatting:
    def test_format_tool_status_read(self):
        from bot.formatting import format_tool_status
        result = format_tool_status("Read", {"file_path": "/foo/bar/config.py"})
        assert "config.py" in result

    def test_format_tool_status_bash(self):
        from bot.formatting import format_tool_status
        result = format_tool_status("Bash", {"command": "ls -la"})
        assert "ls -la" in result

    def test_format_tool_status_bash_long_cmd(self):
        from bot.formatting import format_tool_status
        long_cmd = "a" * 100
        result = format_tool_status("Bash", {"command": long_cmd})
        # Should be truncated
        assert len(result) < 100

    def test_format_tool_status_write(self):
        from bot.formatting import format_tool_status
        result = format_tool_status("Write", {"file_path": "/tmp/output.txt"})
        assert "output.txt" in result

    def test_format_tool_status_glob(self):
        from bot.formatting import format_tool_status
        result = format_tool_status("Glob", {"pattern": "**/*.py"})
        assert "**/*.py" in result

    def test_format_tool_status_grep(self):
        from bot.formatting import format_tool_status
        result = format_tool_status("Grep", {"pattern": "TODO"})
        assert "TODO" in result

    def test_format_tool_status_web_search(self):
        from bot.formatting import format_tool_status
        result = format_tool_status("WebSearch", {})
        assert "web" in result.lower()

    def test_format_tool_status_unknown_tool(self):
        from bot.formatting import format_tool_status
        result = format_tool_status("CustomTool", {})
        assert "CustomTool" in result

    def test_finished_line(self):
        from bot.formatting import finished_line
        result = finished_line("\U0001f4c4 Reading config.py...")
        assert result.startswith("\u2713")
        assert "Reading config.py" in result
        assert not result.endswith("...")

    def test_finished_line_no_emoji(self):
        from bot.formatting import finished_line
        result = finished_line("plain text line")
        assert result.startswith("\u2713")
