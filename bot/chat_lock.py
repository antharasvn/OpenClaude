"""Per-chat asyncio.Lock manager for serializing message processing.

Ensures that for any given chat+thread+user session, only one message is
being processed at a time.  This prevents responses from appearing out of
order when concurrent_updates=True.

Uses a WeakValueDictionary so that locks for inactive chats are garbage
collected automatically once no coroutine holds a reference.
"""

import asyncio
import contextlib
import logging
import weakref

logger = logging.getLogger(__name__)

# WeakValueDictionary: lock is GC'd once no coroutine holds a reference
_chat_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

# Strong references to prevent GC while lock is in use.
# We add a reference when the lock is acquired and remove it on release.
_chat_locks_strong: dict[str, asyncio.Lock] = {}

# Track which asyncio.Task holds each lock
_lock_holders: dict[str, asyncio.Task] = {}


def get_chat_lock(session_key: str) -> asyncio.Lock:
    """Get or create a per-session asyncio.Lock.

    The lock is stored in a WeakValueDictionary. While any coroutine holds
    a strong reference (via the context manager), it won't be GC'd.
    When all references are released, the lock is automatically cleaned up.
    """
    lock = _chat_locks.get(session_key)
    if lock is None:
        lock = asyncio.Lock()
        _chat_locks[session_key] = lock
        # Keep a strong reference so it doesn't get GC'd immediately
        _chat_locks_strong[session_key] = lock
    return lock


def set_lock_holder(session_key: str) -> None:
    """Record the current asyncio.Task as the holder of the lock."""
    task = asyncio.current_task()
    if task is not None:
        _lock_holders[session_key] = task


def release_chat_lock_ref(session_key: str) -> None:
    """Remove the strong reference for a session key.

    Called after the lock is released so that inactive locks can be GC'd.
    Only removes the strong reference if the lock is not currently locked
    (i.e., no one else is waiting on or holding it).
    """
    _lock_holders.pop(session_key, None)
    lock = _chat_locks_strong.get(session_key)
    if lock is not None and not lock.locked():
        _chat_locks_strong.pop(session_key, None)


def force_release_chat_lock(session_key: str) -> None:
    """Force-release a chat lock (for /stop and error recovery).

    Only releases the lock if the recorded holder is done or matches the
    current task. This prevents accidentally releasing a lock held by a
    different coroutine.
    """
    holder = _lock_holders.get(session_key)
    lock = _chat_locks_strong.get(session_key)
    if lock is not None and lock.locked():
        current = asyncio.current_task()
        # Release if: no holder recorded, holder is done, or we ARE the holder
        if holder is None or holder.done() or holder is current:
            with contextlib.suppress(RuntimeError):
                lock.release()
            _lock_holders.pop(session_key, None)
            _chat_locks_strong.pop(session_key, None)
        else:
            logger.warning(
                "force_release_chat_lock(%s): lock held by different active task, skipping",
                session_key,
            )
