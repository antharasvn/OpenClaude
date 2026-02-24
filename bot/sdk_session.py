"""SDKSession class, idle cleanup, shutdown."""

import asyncio
import os
import signal
import time

from bot.config import SDK_IDLE_TIMEOUT
from bot.logging_setup import logger

# Claude Code SDK — persistent session support
try:
    from claude_code_sdk import (
        ClaudeSDKClient,
        ClaudeCodeOptions,
        AssistantMessage,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
        ToolResultBlock,
        PermissionResultAllow,
        PermissionResultDeny,
    )
    from claude_code_sdk.types import StreamEvent

    # Patch SDK to skip unknown message types (e.g. rate_limit_event)
    import claude_code_sdk._internal.message_parser as _mp
    _original_parse = _mp.parse_message
    def _patched_parse(data):
        try:
            return _original_parse(data)
        except _mp.MessageParseError:
            return None
    _mp.parse_message = _patched_parse
    import claude_code_sdk._internal.client as _cl
    _cl.parse_message = _patched_parse

    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    # Provide stub names so type hints don't crash
    ClaudeSDKClient = None
    ClaudeCodeOptions = None
    AssistantMessage = None
    ResultMessage = None
    TextBlock = None
    ToolUseBlock = None
    ToolResultBlock = None
    PermissionResultAllow = None
    PermissionResultDeny = None
    StreamEvent = None

# Global dict: session_key -> SDKSession
sdk_sessions: dict[str, "SDKSession"] = {}


DISCONNECT_TIMEOUT = 10  # seconds


def _kill_tree(pid: int) -> None:
    """Recursively SIGKILL a process and all its descendants."""
    # Collect all descendant PIDs first (bottom-up)
    children = []
    try:
        with open(f"/proc/{pid}/task/{pid}/children") as f:
            child_pids = [int(p) for p in f.read().split()]
        for cpid in child_pids:
            children.extend(_get_descendants(cpid))
            children.append(cpid)
    except (FileNotFoundError, ValueError, OSError):
        pass

    # Kill children bottom-up, then the root
    for cpid in reversed(children):
        try:
            os.kill(cpid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
    try:
        os.kill(pid, signal.SIGKILL)
        logger.info("Hard-killed process tree rooted at pid=%d (%d children)", pid, len(children))
    except ProcessLookupError:
        pass


def _get_descendants(pid: int) -> list[int]:
    """Get all descendant PIDs of a process."""
    result = []
    try:
        with open(f"/proc/{pid}/task/{pid}/children") as f:
            child_pids = [int(p) for p in f.read().split()]
        for cpid in child_pids:
            result.extend(_get_descendants(cpid))
            result.append(cpid)
    except (FileNotFoundError, ValueError, OSError):
        pass
    return result


class SDKSession:
    """Wraps a ClaudeSDKClient with lifecycle management."""

    def __init__(self):
        self.client = None
        self.session_id: str | None = None
        self.last_activity: float = time.time()
        self.connected: bool = False

    async def ensure_connected(self, options) -> None:
        """Connect the SDK client if not already connected."""
        if self.connected and self.client:
            return
        self.client = ClaudeSDKClient(options=options)
        try:
            await self.client.connect()
        except Exception:
            # connect() may have spawned a subprocess before failing —
            # kill it so it doesn't become an orphan
            self.hard_kill()
            self.client = None
            self.connected = False
            raise
        self.connected = True
        self.last_activity = time.time()

    def _get_subprocess_pid(self) -> int | None:
        """Extract the PID of the underlying Claude Code subprocess."""
        try:
            return self.client._query.transport._process.pid
        except (AttributeError, TypeError):
            return None

    def hard_kill(self) -> None:
        """Kill the subprocess and all its descendants (SIGKILL)."""
        pid = self._get_subprocess_pid()
        if not pid:
            return
        _kill_tree(pid)

    async def disconnect(self) -> None:
        """Disconnect the SDK client (with timeout to prevent hangs)."""
        if self.client:
            try:
                await asyncio.wait_for(self.client.disconnect(), timeout=DISCONNECT_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning("SDKSession disconnect timed out after %ds — hard-killing", DISCONNECT_TIMEOUT)
                self.hard_kill()
            except Exception as e:
                logger.warning("SDKSession disconnect error: %s — hard-killing", e)
                self.hard_kill()
            finally:
                self.client = None
                self.connected = False


async def cleanup_idle_sessions():
    """Periodic task to disconnect idle SDK sessions."""
    from bot.streams import load_active_streams
    while True:
        try:
            await asyncio.sleep(60)
            now = time.time()
            active = load_active_streams()
            expired = [k for k, s in sdk_sessions.items()
                       if now - s.last_activity > SDK_IDLE_TIMEOUT
                       and k not in active]
            for key in expired:
                session = sdk_sessions.pop(key, None)
                if session:
                    logger.info("Disconnecting idle SDK session: %s", key)
                    await session.disconnect()
        except Exception:
            logger.exception("Error in cleanup_idle_sessions loop")


async def shutdown_sdk_sessions():
    """Disconnect all SDK sessions (called on bot shutdown)."""
    tasks = []
    for key, session in list(sdk_sessions.items()):
        logger.info("Shutting down SDK session: %s", key)
        tasks.append(session.disconnect())
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    sdk_sessions.clear()
