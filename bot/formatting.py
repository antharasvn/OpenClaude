"""UI formatting helpers for tool status lines."""

from pathlib import Path


def format_tool_status(tool_name: str, tool_input: dict) -> str:
    """Format a human-readable status line for an active tool call."""
    if tool_name == "Read":
        path = tool_input.get("file_path", "file")
        return f"\U0001f4c4 Reading {Path(path).name}..."
    if tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        return f"\U0001f50d Searching {pattern}..."
    if tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        return f'\U0001f50d Searching for "{pattern}"...'
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if cmd:
            short_cmd = cmd[:60] + "\u2026" if len(cmd) > 60 else cmd
            return f"\u2699\ufe0f `{short_cmd}`"
        desc = tool_input.get("description", "")
        if desc:
            return f"\u2699\ufe0f {desc}"
        return "\u2699\ufe0f Running command..."
    if tool_name in ("Write", "Edit"):
        path = tool_input.get("file_path", "file")
        return f"\u270f\ufe0f Editing {Path(path).name}..."
    if tool_name == "WebSearch":
        return "\U0001f310 Searching web..."
    if tool_name == "WebFetch":
        url = tool_input.get("url", "")
        return f"\U0001f310 Fetching {url[:60]}..."
    if tool_name == "Task":
        return "\U0001f916 Delegating to sub-agent..."
    return f"\U0001f527 Using {tool_name}..."


def finished_line(active_line: str) -> str:
    """Convert an active tool status line to a finished (checkmark) line."""
    text = active_line
    idx = text.find(" ")
    if idx != -1:
        text = text[idx + 1:]
    text = text.rstrip(".")
    return f"\u2713 {text}"
