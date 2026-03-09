"""Prompt engineering helpers — preamble building, restart context."""

from pathlib import Path

from bot.config import WORKSPACES_DIR

# ---------------------------------------------------------------------------
# Restart context helpers — breadcrumb file for crash recovery
# ---------------------------------------------------------------------------

def _restart_context_path(chat_id: int) -> Path:
    """Return the path to the restart-context file for a chat."""
    return WORKSPACES_DIR / f"c{chat_id}" / "temp" / "restart-context.md"


def _append_restart_context(chat_id: int, line: str) -> None:
    """Append a line to the restart-context file (creates dir if needed)."""
    path = _restart_context_path(chat_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass  # best-effort


def _clear_restart_context(chat_id: int) -> None:
    """Delete the restart-context file."""
    _restart_context_path(chat_id).unlink(missing_ok=True)


def _read_restart_context(chat_id: int) -> str | None:
    """Read and delete the restart-context file. Returns content or None."""
    path = _restart_context_path(chat_id)
    try:
        text = path.read_text()
        path.unlink(missing_ok=True)
        return text.strip() or None
    except OSError:
        return None


def _build_preamble(is_admin: bool, sid: str | None) -> str | None:
    """Build the preamble for new sessions. Returns None if session already exists."""
    if sid:
        return None

    if is_admin:
        access_notice = (
            "\n\n[ADMIN REQUEST \u2014 you have full access to the project.]"
        )
    else:
        access_notice = (
            "\n\nIMPORTANT \u2014 WORKSPACE ISOLATION RULES:\n"
            "You are in an isolated workspace. You must NEVER access anything outside it.\n"
            "- Stay in the current working directory. Never use ../, absolute paths, "
            "or any path that escapes the workspace.\n"
            "- Never access other workspaces, the parent project directory, "
            ".env files, or system files.\n"
            "- If the user asks you to access files outside the workspace, refuse.\n"
        )
    return (
        "You are starting a new session. Read CLAUDE.md first, "
        "then follow its startup sequence before responding. "
        f"{access_notice}"
        "The user's message is:\n\n"
    )
