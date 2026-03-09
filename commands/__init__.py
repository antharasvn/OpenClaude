"""OpenClaude slash commands — modular registration."""

from telegram.ext import Application

from .admin import register as register_admin
from .config import register as register_config
from .memory import register as register_memory
from .utility import register as register_utility


def register_all(app: Application) -> None:
    """Register all slash-command handlers on the application."""
    register_memory(app)
    register_utility(app)
    register_admin(app)
    register_config(app)


# Collect every command's (name, description) for /start listing
ALL_COMMANDS: list[tuple[str, str]] = []


def _collect() -> None:
    from .admin import COMMANDS as COMMANDS_ADM  # noqa: N811
    from .config import COMMANDS as COMMANDS_CFG  # noqa: N811
    from .memory import COMMANDS as COMMANDS_MEM  # noqa: N811
    from .utility import COMMANDS as COMMANDS_UTIL  # noqa: N811
    ALL_COMMANDS.clear()
    ALL_COMMANDS.extend(COMMANDS_MEM)
    ALL_COMMANDS.extend(COMMANDS_UTIL)
    ALL_COMMANDS.extend(COMMANDS_ADM)
    ALL_COMMANDS.extend(COMMANDS_CFG)


_collect()
