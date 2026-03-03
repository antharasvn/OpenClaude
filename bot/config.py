"""Configuration loading (pydantic-settings based, with backward-compatible module-level attributes)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from the package's parent directory (OpenClaude/)
SCRIPT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SCRIPT_DIR / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(SCRIPT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Fields loaded from environment ---
    telegram_bot_token: SecretStr = SecretStr("")
    allowed_users: str = Field(default="", validation_alias="ALLOWED_USERS")
    claude_model: str = ""
    working_dir: str = Field(default=str(SCRIPT_DIR))

    def model_post_init(self, __context: object) -> None:
        # working_dir: fall back to SCRIPT_DIR if empty
        if not self.working_dir:
            object.__setattr__(self, "working_dir", str(SCRIPT_DIR))

    # --- Derived properties ---

    @property
    def allowed_users_set(self) -> set[int]:
        """Parse ALLOWED_USERS into a set of ints."""
        result: set[int] = set()
        raw = self.allowed_users.strip()
        if raw:
            for uid in raw.split(","):
                uid = uid.strip()
                if uid.isdigit():
                    result.add(int(uid))
        return result

    @property
    def allowed_users_list(self) -> list[int]:
        """Parse ALLOWED_USERS into an ordered list of ints."""
        result: list[int] = []
        raw = self.allowed_users.strip()
        if raw:
            for uid in raw.split(","):
                uid = uid.strip()
                if uid.isdigit():
                    result.append(int(uid))
        return result

    @property
    def admin_user_id(self) -> Optional[int]:
        lst = self.allowed_users_list
        return lst[0] if lst else None

    # --- Fixed paths ---

    @property
    def workspaces_dir(self) -> Path:
        return SCRIPT_DIR / "workspaces"

    @property
    def session_file(self) -> Path:
        return Path.home() / ".openclaude-sessions.json"

    @property
    def active_streams_file(self) -> Path:
        return SCRIPT_DIR / ".active-streams.json"

    @property
    def restart_state_file(self) -> Path:
        return SCRIPT_DIR / ".restart-state.json"

    @property
    def restart_messages_file(self) -> Path:
        return SCRIPT_DIR / ".restart-messages.json"

    @property
    def logs_dir(self) -> Path:
        return SCRIPT_DIR / "logs"

    # --- Constants ---
    ALL_TOOLS: str = "Read,Write,Edit,Bash,Glob,Grep,WebFetch,WebSearch,Task,Skill"
    TELEGRAM_MAX_LENGTH: int = 4096
    CLAUDE_TIMEOUT: int = 300
    STATUS_EDIT_INTERVAL: float = 1.5
    BATCH_WINDOW: float = 1.5
    SDK_IDLE_TIMEOUT: int = 300


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Backward-compatible module-level attributes
# ---------------------------------------------------------------------------
# These let existing code like `from bot.config import ALLOWED_USERS` keep working
# without any changes to the importing modules.

_settings = get_settings()

TELEGRAM_BOT_TOKEN: str = _settings.telegram_bot_token.get_secret_value()
ALLOWED_USERS_RAW: str = _settings.allowed_users
CLAUDE_MODEL: str = _settings.claude_model
WORKING_DIR: str = _settings.working_dir

WORKSPACES_DIR: Path = _settings.workspaces_dir
ALLOWED_USERS: set[int] = _settings.allowed_users_set
ALLOWED_USERS_LIST: list[int] = _settings.allowed_users_list
ADMIN_USER_ID: Optional[int] = _settings.admin_user_id

SESSION_FILE: Path = _settings.session_file
ALL_TOOLS: str = _settings.ALL_TOOLS
TELEGRAM_MAX_LENGTH: int = _settings.TELEGRAM_MAX_LENGTH
CLAUDE_TIMEOUT: int = _settings.CLAUDE_TIMEOUT
ACTIVE_STREAMS_FILE: Path = _settings.active_streams_file
RESTART_STATE_FILE: Path = _settings.restart_state_file
RESTART_MESSAGES_FILE: Path = _settings.restart_messages_file
STATUS_EDIT_INTERVAL: float = _settings.STATUS_EDIT_INTERVAL
BATCH_WINDOW: float = _settings.BATCH_WINDOW
SDK_IDLE_TIMEOUT: int = _settings.SDK_IDLE_TIMEOUT
LOGS_DIR: Path = _settings.logs_dir


# ---------------------------------------------------------------------------
# Backward-compatible functions
# ---------------------------------------------------------------------------

def get_claude_model() -> str:
    """Get current CLAUDE_MODEL."""
    return CLAUDE_MODEL or ""


def set_claude_model(model: str) -> None:
    """Update CLAUDE_MODEL at runtime."""
    global CLAUDE_MODEL
    CLAUDE_MODEL = model


def is_authorized(user_id: int) -> bool:
    """Check if a user is authorized to use the bot."""
    if not ALLOWED_USERS:
        return False
    return user_id in ALLOWED_USERS


def get_thread_id(update: object) -> int:
    """Get the forum topic thread ID, or 0 for non-forum messages."""
    msg = getattr(update, "message", None)
    return msg.message_thread_id if msg and getattr(msg, "message_thread_id", None) else 0
