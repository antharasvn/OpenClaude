"""OS-level process management for active Claude subprocesses."""

import asyncio
import logging
import os
import signal

logger = logging.getLogger(__name__)


# Active subprocess references for /stop support
_active_procs: dict[str, asyncio.subprocess.Process] = {}

# Cache the bot's own process group so we never kill ourselves
_BOT_PGID = os.getpgid(os.getpid())


def kill_active_proc(skey: str) -> bool:
    """Kill the active subprocess and all its children. Returns True if killed."""
    from bot.sdk_session import _kill_tree
    proc = _active_procs.pop(skey, None)
    if proc and proc.returncode is None:
        try:
            # Try process-group kill first (catches background sub-agents)
            pid = proc.pid
            try:
                pgid = os.getpgid(pid)
                if pgid != _BOT_PGID:
                    os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass
            # Fallback: pick off stragglers that changed their pgid
            _kill_tree(pid)
            return True
        except Exception:
            try:
                proc.kill()
                return True
            except ProcessLookupError:
                pass
    return False
