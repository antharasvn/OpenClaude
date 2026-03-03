"""OS-level process management for active Claude subprocesses."""

import asyncio

from bot.logging_setup import logger


# Active subprocess references for /stop support
_active_procs: dict[str, asyncio.subprocess.Process] = {}


def kill_active_proc(skey: str) -> bool:
    """Kill the active subprocess and all its children. Returns True if killed."""
    from bot.sdk_session import _kill_tree, _killpg_safe
    proc = _active_procs.pop(skey, None)
    if proc and proc.returncode is None:
        try:
            # Try process-group kill first (catches background sub-agents)
            _killpg_safe(proc.pid)
            # Fallback: pick off stragglers that changed their pgid
            _kill_tree(proc.pid)
            return True
        except Exception:
            try:
                proc.kill()
                return True
            except ProcessLookupError:
                pass
    return False
