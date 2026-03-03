"""Shared utility functions."""


def format_size(size_bytes: int | float) -> str:
    """Format a byte count as a human-readable string (e.g. '1.2MB', '45KB', '100B')."""
    if size_bytes > 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f}MB"
    elif size_bytes > 1024:
        return f"{size_bytes / 1024:.0f}KB"
    else:
        return f"{int(size_bytes)}B"


def context_bar(used: int, total: int, width: int = 20) -> str:
    """Build a text progress bar: [========····] 42%"""
    pct = min(used / total, 1.0) if total else 0
    filled = round(pct * width)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    return f"[{bar}] {pct:.0%}"
