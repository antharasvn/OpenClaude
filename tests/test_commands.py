"""Tests for commands: config, memory, admin, utility."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from commands.config import (
    ToggleSetting,
    _get_setting,
    _load_settings,
    _save_settings,
    _set_setting,
    get_respond_mode,
    get_streaming,
    get_verbose,
)

# ======================================================================
# Helper factories
# ======================================================================


def _make_update(user_id=111111, chat_id=123, chat_type="private", thread_id=0):
    """Create a mock Telegram Update."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_chat.type = chat_type

    message = AsyncMock()
    message.reply_text = AsyncMock()
    message.message_thread_id = thread_id or None
    update.message = message

    return update


def _make_callback_query(user_id=111111, data="streaming:on:123:0"):
    """Create a mock callback query."""
    query = AsyncMock()
    query.from_user = MagicMock()
    query.from_user.id = user_id
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock()
    update.callback_query = query
    return update


def _make_context(**kwargs):
    ctx = MagicMock()
    ctx.args = kwargs.get("args", [])
    ctx.bot = AsyncMock()
    return ctx


# ======================================================================
# ToggleSetting
# ======================================================================


class TestToggleSetting:
    def test_text_on(self):
        toggle = ToggleSetting(
            key="test",
            label="Test Setting",
            default=False,
            on_desc="It's on!",
            off_desc="It's off!",
        )
        text = toggle.text(True)
        assert "ON" in text
        assert "It's on!" in text
        assert "Test Setting" in text

    def test_text_off(self):
        toggle = ToggleSetting(
            key="test",
            label="Test Setting",
            default=False,
            on_desc="It's on!",
            off_desc="It's off!",
        )
        text = toggle.text(False)
        assert "OFF" in text
        assert "It's off!" in text

    def test_keyboard_on(self):
        toggle = ToggleSetting(
            key="mykey",
            label="My Setting",
            default=False,
            on_desc="on",
            off_desc="off",
        )
        kb = toggle.keyboard(True, 123, 0)
        buttons = kb.inline_keyboard[0]
        assert len(buttons) == 2
        assert "\u2713" in buttons[0].text
        assert "mykey:on:123:0" in buttons[0].callback_data

    def test_keyboard_off(self):
        toggle = ToggleSetting(
            key="mykey",
            label="My Setting",
            default=True,
            on_desc="on",
            off_desc="off",
        )
        kb = toggle.keyboard(False, 456, 7)
        buttons = kb.inline_keyboard[0]
        assert "\u2713" in buttons[1].text
        assert "mykey:off:456:7" in buttons[1].callback_data

    @pytest.mark.asyncio
    async def test_callback_handler_authorized(self):
        toggle = ToggleSetting(
            key="streaming",
            label="Streaming",
            default=False,
            on_desc="On",
            off_desc="Off",
        )
        update = _make_callback_query(user_id=111111, data="streaming:on:123:0")
        context = _make_context()

        with patch("commands.config.is_authorized", return_value=True):
            with patch.object(toggle, "set") as mock_set:
                await toggle.callback_handler(update, context)
                mock_set.assert_called_once_with(123, 0, True)

            update.callback_query.answer.assert_called()
            update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_handler_unauthorized(self):
        toggle = ToggleSetting(
            key="streaming",
            label="Streaming",
            default=False,
            on_desc="On",
            off_desc="Off",
        )
        update = _make_callback_query(user_id=999999, data="streaming:on:123:0")
        context = _make_context()

        with patch("commands.config.is_authorized", return_value=False):
            await toggle.callback_handler(update, context)
            update.callback_query.answer.assert_called_once_with("Unauthorized", show_alert=True)

    @pytest.mark.asyncio
    async def test_callback_handler_invalid_data(self):
        toggle = ToggleSetting(
            key="streaming",
            label="Streaming",
            default=False,
            on_desc="On",
            off_desc="Off",
        )
        update = _make_callback_query(user_id=111111, data="streaming:on")
        context = _make_context()

        with patch("commands.config.is_authorized", return_value=True), \
             patch.object(toggle, "set") as mock_set:
            await toggle.callback_handler(update, context)
            mock_set.assert_not_called()


# ======================================================================
# Settings persistence
# ======================================================================


class TestSettingsPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        settings_file = tmp_path / "chat-settings.json"
        with patch("commands.config._settings_file", return_value=settings_file), \
             patch("commands.config._settings_cache", None), \
             patch("commands.config._settings_mtime", 0.0):
            _save_settings({"123:0": {"streaming": True}})
            loaded = _load_settings()
            assert loaded == {"123:0": {"streaming": True}}

    def test_get_setting_default(self, tmp_path):
        settings_file = tmp_path / "nonexistent.json"
        with patch("commands.config._settings_file", return_value=settings_file), \
             patch("commands.config._settings_cache", None):
            result = _get_setting(123, 0, "streaming", False)
            assert result is False

    def test_set_and_get_setting(self, tmp_path):
        settings_file = tmp_path / "chat-settings.json"
        with patch("commands.config._settings_file", return_value=settings_file), \
             patch("commands.config._settings_cache", None), \
             patch("commands.config._settings_mtime", 0.0):
            _set_setting(123, 0, "streaming", True)
            result = _get_setting(123, 0, "streaming", False)
            assert result is True


class TestPublicGetters:
    def test_get_streaming_default_false(self):
        with patch("commands.config._load_settings", return_value={}):
            assert get_streaming(123, 0) is False

    def test_get_verbose_default_true(self):
        with patch("commands.config._load_settings", return_value={}):
            assert get_verbose(123, 0) is True

    def test_get_respond_mode_default_all(self):
        with patch("commands.config._load_settings", return_value={}):
            assert get_respond_mode(123, 0) == "all"


# ======================================================================
# Callback auth (respond command)
# ======================================================================


class TestRespondCallback:
    @pytest.mark.asyncio
    async def test_callback_respond_unauthorized(self):
        from commands.config import callback_respond

        update = _make_callback_query(user_id=999999, data="respond:all:123:0")
        context = _make_context()

        await callback_respond(update, context)
        update.callback_query.answer.assert_called_once_with("Unauthorized", show_alert=True)

    @pytest.mark.asyncio
    async def test_callback_respond_authorized(self):
        from commands.config import callback_respond

        update = _make_callback_query(user_id=111111, data="respond:mention:123:0")
        context = _make_context()

        with patch("commands.config.is_authorized", return_value=True), \
             patch("commands.config._set_setting") as mock_set:
            await callback_respond(update, context)
            mock_set.assert_called_once_with(123, 0, "respond_mode", "mention")

    @pytest.mark.asyncio
    async def test_callback_respond_invalid_mode(self):
        from commands.config import callback_respond

        update = _make_callback_query(user_id=111111, data="respond:invalid:123:0")
        context = _make_context()

        with patch("commands.config.is_authorized", return_value=True), \
             patch("commands.config._set_setting") as mock_set:
            await callback_respond(update, context)
            mock_set.assert_not_called()


# ======================================================================
# Auth decorators
# ======================================================================


class TestAuthDecorators:
    @pytest.mark.asyncio
    async def test_authorized_allows_valid_user(self):
        from bot.auth import authorized

        @authorized
        async def handler(update, context):
            return "success"

        update = _make_update(user_id=111111, chat_type="private")
        context = _make_context()

        with patch("bot.auth.is_authorized", return_value=True), \
             patch("bot.routing.should_respond", return_value=True):
            result = await handler(update, context)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_authorized_blocks_invalid_user(self):
        from bot.auth import authorized

        @authorized
        async def handler(update, context):
            return "success"

        update = _make_update(user_id=999999)
        context = _make_context()

        with patch("bot.auth.is_authorized", return_value=False):
            result = await handler(update, context)
        assert result is None

    @pytest.mark.asyncio
    async def test_authorized_only_allows_valid_user(self):
        from bot.auth import authorized_only

        @authorized_only
        async def handler(update, context):
            return "success"

        update = _make_update(user_id=111111)
        context = _make_context()

        with patch("bot.auth.is_authorized", return_value=True):
            result = await handler(update, context)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_authorized_only_blocks_invalid_user(self):
        from bot.auth import authorized_only

        @authorized_only
        async def handler(update, context):
            return "success"

        update = _make_update(user_id=999999)
        context = _make_context()

        with patch("bot.auth.is_authorized", return_value=False):
            result = await handler(update, context)
        assert result is None

    @pytest.mark.asyncio
    async def test_admin_only_blocks_non_admin(self):
        from bot.auth import admin_only

        @admin_only
        async def handler(update, context):
            return "success"

        update = _make_update(user_id=222222)
        context = _make_context()

        with patch("bot.auth.is_admin", return_value=False):
            result = await handler(update, context)
        assert result is None
        update.message.reply_text.assert_called_once_with("Admin only.")


# ======================================================================
# Routing
# ======================================================================


class TestRouting:
    def test_private_chat_always_responds(self):
        from bot.routing import should_respond

        update = _make_update(chat_type="private")
        assert should_respond(update) is True

    def test_group_all_mode_responds(self):
        from bot.routing import should_respond

        update = _make_update(chat_type="group", chat_id=123, thread_id=0)
        with patch("commands.config.get_respond_mode", return_value="all"):
            assert should_respond(update) is True

    def test_group_mention_mode_no_mention(self):
        from bot.routing import should_respond

        update = _make_update(chat_type="group", chat_id=123, thread_id=0)
        update.message.entities = None
        update.message.reply_to_message = None
        with patch("commands.config.get_respond_mode", return_value="mention"):
            assert should_respond(update) is False

    def test_strip_bot_mention(self):
        import bot.routing
        from bot.routing import strip_bot_mention

        bot.routing.BOT_USERNAME = "TestBot"
        result = strip_bot_mention("@TestBot hello there")
        assert result == "hello there"
        bot.routing.BOT_USERNAME = ""

    def test_strip_bot_mention_empty_username(self):
        import bot.routing
        from bot.routing import strip_bot_mention

        bot.routing.BOT_USERNAME = ""
        result = strip_bot_mention("@TestBot hello")
        assert result == "@TestBot hello"
