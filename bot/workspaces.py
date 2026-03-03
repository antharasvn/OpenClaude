"""Per-chat workspace creation, symlinks, memory."""

import os
import shutil
from pathlib import Path

from bot.config import WORKSPACES_DIR, WORKING_DIR
import logging

logger = logging.getLogger(__name__)

# Shared files are symlinked into each workspace so updates propagate automatically
_SYMLINKED_FILES = ["TOOLS.md", "CLAUDE.md", "AGENTS.md"]
_SYMLINKED_DIRS = [".claude"]
# BOOTSTRAP.md is always freshly copied so new sessions run the first-run ritual
_BOOTSTRAP_FILE = "BOOTSTRAP.md"

# ---------------------------------------------------------------------------
# Workspace existence cache — skip filesystem ops for already-initialized chats
# ---------------------------------------------------------------------------
_initialized_workspaces: set[int] = set()


def ensure_workspace(chat_id: int) -> Path:
    """Create and return an isolated workspace directory for the given chat.

    Workspace layout:
      workspaces/c{chat_id}/
        TOOLS.md       -> symlink to ../../TOOLS.md
        CLAUDE.md      -> symlink to ../../CLAUDE.md
        .claude/       -> symlink to ../../.claude
        IDENTITY.md    <- independent copy (set up via BOOTSTRAP.md)
        USER.md        <- independent copy
        BOOTSTRAP.md   <- fresh copy every new session
        memory/        <- isolated per-chat memory
          MEMORY.md
    """
    # Fast path: if we already initialized this workspace this process lifetime, skip
    if chat_id in _initialized_workspaces:
        return WORKSPACES_DIR / f"c{chat_id}"

    workspace = WORKSPACES_DIR / f"c{chat_id}"
    is_new = not workspace.exists()

    workspace.mkdir(parents=True, exist_ok=True)
    base = Path(WORKING_DIR)

    _sync_workspace_links(workspace)

    # Copy BOOTSTRAP.md if the workspace hasn't been initialized yet
    # (directory may already exist because the logger creates it early)
    _initialized = (workspace / "IDENTITY.md").exists()
    if not _initialized:
        bootstrap = base / _BOOTSTRAP_FILE
        if bootstrap.exists():
            shutil.copy2(bootstrap, workspace / _BOOTSTRAP_FILE)

    # Create isolated memory directory
    mem_dir = workspace / "memory"
    mem_dir.mkdir(exist_ok=True)
    mem_template = base / "memory" / "MEMORY.md"
    mem_dst = mem_dir / "MEMORY.md"
    if mem_template.exists() and not mem_dst.exists():
        shutil.copy2(mem_template, mem_dst)

    # Symlink t0/MEMORY.md → ../MEMORY.md so Claude uses a uniform write path
    t0_dir = mem_dir / "t0"
    t0_dir.mkdir(exist_ok=True)
    t0_mem = t0_dir / "MEMORY.md"
    if not t0_mem.exists():
        t0_mem.symlink_to("../MEMORY.md")

    if is_new:
        logger.info("Created workspace for chat %d at %s", chat_id, workspace)

    # Add to cache after successful initialization
    _initialized_workspaces.add(chat_id)
    return workspace


def _sync_workspace_links(workspace: Path) -> None:
    """Ensure symlinks in an existing workspace point to current shared files."""
    base = Path(WORKING_DIR)
    for fname in _SYMLINKED_FILES:
        src = base / fname
        dst = workspace / fname
        if src.exists() and not dst.exists():
            dst.symlink_to(os.path.relpath(src, workspace))
    for dname in _SYMLINKED_DIRS:
        src = base / dname
        dst = workspace / dname
        if src.exists() and not dst.exists():
            dst.symlink_to(os.path.relpath(src, workspace))


def get_working_dir(chat_id: int) -> str:
    """Return the working directory for a given chat."""
    return str(ensure_workspace(chat_id))
