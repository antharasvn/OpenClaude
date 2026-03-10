"""Prompt engineering helpers — preamble building, restart context."""

import subprocess
from pathlib import Path

from bot.config import WORKSPACES_DIR

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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


def _get_current_commit() -> str:
    """Return the short hash of the current git HEAD commit."""
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _restart_commit_path(chat_id: int) -> Path:
    """Return the path to the restart-commit file for a chat."""
    return WORKSPACES_DIR / f"c{chat_id}" / "temp" / "restart-commit.txt"


def _record_restart_commit(chat_id: int) -> None:
    """Write the current git commit hash to restart-commit.txt (best-effort)."""
    path = _restart_commit_path(chat_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_get_current_commit())
    except OSError:
        pass


def _read_restart_commit(chat_id: int) -> str | None:
    """Read and delete the restart-commit file. Returns commit hash or None."""
    path = _restart_commit_path(chat_id)
    try:
        text = path.read_text().strip()
        path.unlink(missing_ok=True)
        return text or None
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
