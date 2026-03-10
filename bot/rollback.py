"""Rollback notification injection -- shared state and helpers."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from bot.config import ROLLBACK_INFO_FILE

logger = logging.getLogger(__name__)

# In-memory set of session keys that have already received the rollback injection.
# Lost on restart -- that's fine, since the rollback file won't be present after
# a successful restart (record_good() deletes it).
_rollback_consumed: set[str] = set()

ROLLBACK_WINDOW = timedelta(minutes=5)


def _load_rollback_info() -> dict | None:
    """Load .rollback-info.json if it exists and is within the 5-minute window."""
    try:
        if not ROLLBACK_INFO_FILE.exists():
            return None
        data = json.loads(ROLLBACK_INFO_FILE.read_text())
        created = datetime.fromisoformat(data["created"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - created > ROLLBACK_WINDOW:  # noqa: UP017
            return None
        return data
    except Exception:
        return None


def get_rollback_injection(skey: str, session_exists: bool) -> str | None:
    """Return rollback injection text if this session should receive it, else None.

    Conditions:
      - .rollback-info.json exists and is within 5 minutes of creation
      - The session already existed before the rollback (session_exists=True)
      - This session key hasn't already received the injection
    """
    if skey in _rollback_consumed:
        return None
    if not session_exists:
        return None
    info = _load_rollback_info()
    if info is None:
        return None

    # Mark as consumed
    _rollback_consumed.add(skey)

    bad = info.get("bad_commit", "unknown")[:7]
    good = info.get("good_commit", "unknown")[:7]
    test_out = info.get("test_output", "").strip()
    test_section = f"\n\nTest output:\n```\n{test_out[-1000:]}\n```" if test_out else ""

    return (
        f"[System: A git rollback just occurred. "
        f"Bad commit {bad} was reverted to {good} because tests failed.{test_section}\n\n"
        f"Briefly inform the user about this rollback before responding to their message.]"
    )


def mark_consumed(skey: str) -> None:
    """Mark a session key as having already received rollback info (e.g. via restart recovery)."""
    _rollback_consumed.add(skey)
