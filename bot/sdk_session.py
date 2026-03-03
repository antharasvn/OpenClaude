"""SDKSession class, idle cleanup, shutdown."""

import asyncio
import os
import signal
import time

from bot.config import SDK_IDLE_TIMEOUT
import logging

logger = logging.getLogger(__name__)

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

DISCONNECT_TIMEOUT = 10  # seconds

# Cache the bot's own process group so we never kill ourselves
_BOT_PGID = os.getpgid(os.getpid())


def _killpg_safe(pid: int) -> bool:
    """Kill the process group of *pid* via SIGKILL, if it differs from the bot's.

    Returns True if killpg was sent successfully, False otherwise.
    """
    try:
        pgid = os.getpgid(pid)
    except (ProcessLookupError, OSError):
        return False
    if pgid == _BOT_PGID:
        logger.debug("Skipping killpg — pgid %d matches bot's own process group", pgid)
        return False
    try:
        os.killpg(pgid, signal.SIGKILL)
        logger.info("Killed process group pgid=%d (from pid=%d)", pgid, pid)
        return True
    except (ProcessLookupError, PermissionError, OSError) as exc:
        logger.debug("killpg(pgid=%d) failed: %s", pgid, exc)
        return False


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
        """Kill the subprocess and all its descendants (SIGKILL).

        Uses process-group killing first so that background sub-agents
        (which may have been reparented to PID 1) are caught.  Falls
        back to ``_kill_tree`` for any processes that changed their
        process group.
        """
        pid = self._get_subprocess_pid()
        if not pid:
            return
        _killpg_safe(pid)
        # Fallback: pick off any stragglers not in the same pgid
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


class SDKSessionManager:
    """Manages the lifecycle of all SDKSession instances.

    Replaces the former bare ``sdk_sessions`` dict with explicit methods for
    creation, retrieval, disconnection, idle cleanup, and shutdown.
    """

    def __init__(self, idle_timeout: int = SDK_IDLE_TIMEOUT):
        self._sessions: dict[str, SDKSession] = {}
        self._idle_timeout = idle_timeout

    # ── dict-like helpers (backward compat) ──────────────────────────

    def get(self, key: str) -> SDKSession | None:
        """Return the session for *key*, or ``None``."""
        return self._sessions.get(key)

    def pop(self, key: str) -> SDKSession | None:
        """Remove and return the session for *key*, or ``None``."""
        return self._sessions.pop(key, None)

    def __contains__(self, key: str) -> bool:
        return key in self._sessions

    def __len__(self) -> int:
        return len(self._sessions)

    # ── core API ─────────────────────────────────────────────────────

    def get_or_create(self, key: str, session_id: str | None = None) -> SDKSession:
        """Return an existing session or create a new one for *key*."""
        session = self._sessions.get(key)
        if session is None:
            session = SDKSession()
            session.session_id = session_id
            self._sessions[key] = session
        return session

    def put(self, key: str, session: SDKSession) -> None:
        """Store *session* under *key* (replaces any existing entry)."""
        self._sessions[key] = session

    async def disconnect(self, key: str) -> None:
        """Disconnect and remove the session identified by *key*."""
        session = self._sessions.pop(key, None)
        if session:
            logger.info("Disconnecting SDK session: %s", key)
            await session.disconnect()

    async def cleanup_idle(self) -> None:
        """Periodic task — disconnect sessions idle longer than the timeout."""
        from bot.streams import load_active_streams
        while True:
            try:
                await asyncio.sleep(60)
                now = time.time()
                active = load_active_streams()
                expired = [
                    k for k, s in self._sessions.items()
                    if now - s.last_activity > self._idle_timeout
                    and k not in active
                ]
                for key in expired:
                    session = self._sessions.pop(key, None)
                    if session:
                        logger.info("Disconnecting idle SDK session: %s", key)
                        await session.disconnect()
            except Exception:
                logger.exception("Error in SDKSessionManager.cleanup_idle loop")

    async def shutdown_all(self) -> None:
        """Disconnect every session (called on bot shutdown)."""
        tasks = []
        for key, session in list(self._sessions.items()):
            logger.info("Shutting down SDK session: %s", key)
            tasks.append(session.disconnect())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._sessions.clear()


# ── Singleton instance ───────────────────────────────────────────────
sdk_session_manager = SDKSessionManager()

# Backward-compatible alias so existing ``from bot.sdk_session import sdk_sessions``
# still works.  The manager exposes .get / .pop / __contains__ / __len__ but
# callers should migrate to the manager's explicit API.
sdk_sessions = sdk_session_manager


# ── Legacy function shims (thin wrappers around the manager) ─────────

async def cleanup_idle_sessions() -> None:
    """Start the idle-cleanup loop (legacy entry-point)."""
    await sdk_session_manager.cleanup_idle()


async def shutdown_sdk_sessions() -> None:
    """Disconnect all sessions (legacy entry-point)."""
    await sdk_session_manager.shutdown_all()
