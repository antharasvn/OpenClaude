"""Fallback permission result types when claude_code_sdk is not installed."""

from dataclasses import dataclass
from typing import Any


@dataclass
class PermissionResultAllow:
    """Allow permission result."""

    behavior: str = "allow"
    updated_input: dict[str, Any] | None = None


@dataclass
class PermissionResultDeny:
    """Deny permission result."""

    behavior: str = "deny"
    message: str = ""
