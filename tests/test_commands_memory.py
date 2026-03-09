"""Tests for commands/memory.py — /memory, /daily, /save, /remember, /forget, /history."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from commands.memory import (
    cmd_daily,
    cmd_forget,
    cmd_history,
    cmd_memory,
    cmd_remember,
    cmd_save,
    register,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_update(user_id=111111, chat_id=123, thread_id=0):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat = MagicMock()
    update.effective_chat.id = chat_id
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.message.message_thread_id = thread_id or None
    return update


def _make_context(**kwargs):
    ctx = MagicMock()
    ctx.args = kwargs.get("args", [])
    ctx.bot = AsyncMock()
    return ctx


# ---------------------------------------------------------------------------
# /memory
# ---------------------------------------------------------------------------

class TestCmdMemory:
    @pytest.mark.asyncio
    async def test_unauthorized_user_returns_early(self):
        update = _make_update(user_id=999999)
        context = _make_context()

        with patch("commands.memory.is_authorized", return_value=False):
            await cmd_memory(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_shows_memory_content(self, tmp_path):
        update = _make_update()
        context = _make_context()

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        mem_file = mem_dir / "MEMORY.md"
        mem_file.write_text("Remember this fact")

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("commands.memory.ensure_workspace", return_value=tmp_path):
            await cmd_memory(update, context)

        update.message.reply_text.assert_called()
        call_text = update.message.reply_text.call_args_list[0][0][0]
        assert "Remember this fact" in call_text

    @pytest.mark.asyncio
    async def test_shows_not_created_when_no_memory_file(self, tmp_path):
        update = _make_update()
        context = _make_context()

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("commands.memory.ensure_workspace", return_value=tmp_path):
            await cmd_memory(update, context)

        call_text = update.message.reply_text.call_args_list[0][0][0]
        assert "not created yet" in call_text

    @pytest.mark.asyncio
    async def test_shows_topic_memory_for_nonzero_thread(self, tmp_path):
        update = _make_update()
        context = _make_context()

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "MEMORY.md").write_text("workspace memory")
        topic_dir = mem_dir / "t42"
        topic_dir.mkdir()
        (topic_dir / "MEMORY.md").write_text("topic specific memory")

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=42), \
             patch("commands.memory.ensure_workspace", return_value=tmp_path):
            await cmd_memory(update, context)

        # Should have called reply_text at least once with topic memory
        all_text = " ".join(
            call[0][0] for call in update.message.reply_text.call_args_list
        )
        assert "topic specific memory" in all_text


# ---------------------------------------------------------------------------
# /daily
# ---------------------------------------------------------------------------

class TestCmdDaily:
    @pytest.mark.asyncio
    async def test_unauthorized_user_returns_early(self):
        update = _make_update(user_id=999999)
        context = _make_context()

        with patch("commands.memory.is_authorized", return_value=False):
            await cmd_daily(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_date_format(self):
        update = _make_update()
        context = _make_context(args=["not-a-date"])

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("commands.memory.ensure_workspace", return_value=Path("/tmp/ws")):
            await cmd_daily(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "Invalid date" in call_text

    @pytest.mark.asyncio
    async def test_no_daily_logs(self, tmp_path):
        update = _make_update()
        context = _make_context(args=["2026-01-01"])

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("commands.memory.ensure_workspace", return_value=tmp_path):
            await cmd_daily(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "No daily logs" in call_text

    @pytest.mark.asyncio
    async def test_shows_daily_logs(self, tmp_path):
        update = _make_update()
        context = _make_context(args=["2026-03-01"])

        daily_dir = tmp_path / "memory" / "t0" / "2026-03-01"
        daily_dir.mkdir(parents=True)
        (daily_dir / "session.md").write_text("Did some refactoring today")

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("commands.memory.ensure_workspace", return_value=tmp_path):
            await cmd_daily(update, context)

        all_text = " ".join(
            call[0][0] for call in update.message.reply_text.call_args_list
        )
        assert "refactoring" in all_text


# ---------------------------------------------------------------------------
# /save
# ---------------------------------------------------------------------------

class TestCmdSave:
    @pytest.mark.asyncio
    async def test_unauthorized_user_returns_early(self):
        update = _make_update(user_id=999999)
        context = _make_context()

        with patch("commands.memory.is_authorized", return_value=False):
            await cmd_save(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_filename_shows_usage(self):
        update = _make_update()
        context = _make_context(args=[])

        with patch("commands.memory.is_authorized", return_value=True):
            await cmd_save(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "Usage" in call_text

    @pytest.mark.asyncio
    async def test_invalid_filename_rejected(self):
        update = _make_update()
        context = _make_context(args=["bad file!name"])

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0):
            await cmd_save(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "alphanumeric" in call_text

    @pytest.mark.asyncio
    async def test_valid_filename_delegates_to_streaming(self):
        update = _make_update()
        context = _make_context(args=["session-notes"])

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("bot.handlers.run_with_streaming", new_callable=AsyncMock) as mock_rws:
            await cmd_save(update, context)

        mock_rws.assert_called_once()
        assert "session-notes" in str(mock_rws.call_args)

    @pytest.mark.asyncio
    async def test_strips_md_extension(self):
        update = _make_update()
        context = _make_context(args=["notes.md"])

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("bot.handlers.run_with_streaming", new_callable=AsyncMock) as mock_rws:
            await cmd_save(update, context)

        # Should have stripped .md and used "notes"
        prompt_str = str(mock_rws.call_args)
        assert "notes" in prompt_str


# ---------------------------------------------------------------------------
# /remember
# ---------------------------------------------------------------------------

class TestCmdRemember:
    @pytest.mark.asyncio
    async def test_unauthorized_user_returns_early(self):
        update = _make_update(user_id=999999)
        context = _make_context()

        with patch("commands.memory.is_authorized", return_value=False):
            await cmd_remember(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_note_shows_usage(self):
        update = _make_update()
        context = _make_context(args=[])

        with patch("commands.memory.is_authorized", return_value=True):
            await cmd_remember(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "Usage" in call_text

    @pytest.mark.asyncio
    async def test_saves_to_workspace_memory(self, tmp_path):
        update = _make_update()
        context = _make_context(args=["user", "likes", "dark", "mode"])

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir(parents=True)

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("commands.memory.ensure_workspace", return_value=tmp_path):
            await cmd_remember(update, context)

        mem_file = mem_dir / "MEMORY.md"
        assert mem_file.exists()
        content = mem_file.read_text()
        assert "user likes dark mode" in content

        call_text = update.message.reply_text.call_args[0][0]
        assert "workspace memory" in call_text

    @pytest.mark.asyncio
    async def test_saves_to_topic_memory(self, tmp_path):
        update = _make_update()
        context = _make_context(args=["project", "uses", "pytest"])

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=42), \
             patch("commands.memory.ensure_workspace", return_value=tmp_path):
            await cmd_remember(update, context)

        topic_mem = tmp_path / "memory" / "t42" / "MEMORY.md"
        assert topic_mem.exists()
        content = topic_mem.read_text()
        assert "project uses pytest" in content

        call_text = update.message.reply_text.call_args[0][0]
        assert "topic memory" in call_text


# ---------------------------------------------------------------------------
# /forget
# ---------------------------------------------------------------------------

class TestCmdForget:
    @pytest.mark.asyncio
    async def test_unauthorized_user_returns_early(self):
        update = _make_update(user_id=999999)
        context = _make_context()

        with patch("commands.memory.is_authorized", return_value=False):
            await cmd_forget(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_args_shows_usage(self):
        update = _make_update()
        context = _make_context(args=[])

        with patch("commands.memory.is_authorized", return_value=True):
            await cmd_forget(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "Usage" in call_text

    @pytest.mark.asyncio
    async def test_delegates_to_streaming(self):
        update = _make_update()
        context = _make_context(args=["old", "project", "info"])

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("bot.handlers.run_with_streaming", new_callable=AsyncMock) as mock_rws:
            await cmd_forget(update, context)

        mock_rws.assert_called_once()


# ---------------------------------------------------------------------------
# /history
# ---------------------------------------------------------------------------

class TestCmdHistory:
    @pytest.mark.asyncio
    async def test_unauthorized_user_returns_early(self):
        update = _make_update(user_id=999999)
        context = _make_context()

        with patch("commands.memory.is_authorized", return_value=False):
            await cmd_history(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_delegates_to_streaming(self):
        update = _make_update()
        context = _make_context()

        with patch("commands.memory.is_authorized", return_value=True), \
             patch("commands.memory.get_thread_id", return_value=0), \
             patch("bot.handlers.run_with_streaming", new_callable=AsyncMock) as mock_rws:
            await cmd_history(update, context)

        mock_rws.assert_called_once()
        # Prompt should mention "summary"
        prompt = str(mock_rws.call_args)
        assert "summary" in prompt.lower()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_adds_handlers(self):
        app = MagicMock()
        register(app)
        # Should add 6 handlers (memory, daily, save, remember, forget, history)
        assert app.add_handler.call_count == 6
