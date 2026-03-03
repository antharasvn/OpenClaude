"""Logger setup (infra, workspace loggers).

All logging configuration is deferred to ``setup_logging()`` — importing this
module has **no** side effects.  Call ``setup_logging()`` once from ``app.main()``
before any log messages are emitted.
"""

import logging
import logging.handlers

from bot.config import LOGS_DIR, WORKSPACES_DIR, get_settings

# ---------------------------------------------------------------------------
# Module-level loggers — usable immediately after ``setup_logging()`` is called.
# Before that they are plain loggers with no handlers (messages go nowhere).
# ---------------------------------------------------------------------------
logger = logging.getLogger("bot")
infra_logger = logging.getLogger("bot.infra")

_LOG_FORMAT = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

_setup_done = False


def setup_logging() -> None:
    """Configure root + infra loggers.  Safe to call more than once (no-op after first)."""
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Root / console logging
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Structured file logging — infra logger
    LOGS_DIR.mkdir(exist_ok=True)

    infra_logger.propagate = False
    _infra_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "infra.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    _infra_handler.setFormatter(_LOG_FORMAT)
    infra_logger.addHandler(_infra_handler)
    infra_logger.setLevel(level)


# ---------------------------------------------------------------------------
# Workspace logger factory — per-chat activity logs
# ---------------------------------------------------------------------------
_workspace_loggers: dict[int, logging.Logger] = {}


def get_workspace_logger(chat_id: int) -> logging.Logger:
    """Return a cached logger that writes to workspaces/c{chat_id}/logs/activity.log."""
    if chat_id in _workspace_loggers:
        return _workspace_loggers[chat_id]
    ws_log_dir = WORKSPACES_DIR / f"c{chat_id}" / "logs"
    ws_log_dir.mkdir(parents=True, exist_ok=True)
    ws_logger = logging.getLogger(f"bot.ws.{chat_id}")
    ws_logger.propagate = False
    handler = logging.handlers.RotatingFileHandler(
        ws_log_dir / "activity.log", maxBytes=2 * 1024 * 1024, backupCount=2
    )
    handler.setFormatter(_LOG_FORMAT)
    ws_logger.addHandler(handler)
    ws_logger.setLevel(logging.INFO)
    _workspace_loggers[chat_id] = ws_logger
    return ws_logger


def _summarize_input(tool_input: dict) -> str:
    """Truncate a tool input dict to a readable one-liner for log entries."""
    parts = []
    for k, v in tool_input.items():
        v_str = str(v)
        if len(v_str) > 80:
            v_str = v_str[:77] + "..."
        parts.append(f"{k}={v_str}")
    summary = ", ".join(parts)
    return summary[:200] if len(summary) > 200 else summary
