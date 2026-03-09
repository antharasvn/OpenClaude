"""Typed event dataclasses for the Claude streaming pipeline.

These replace the raw dict events yielded by stream_claude() and consumed
by run_with_streaming() in handlers.py.

Event types found in claude.py (both SDK and subprocess paths):
  - partial       → text delta during streaming (verbose mode)
  - text_block    → completed text block from AssistantMessage/TextBlock
  - tool_use      → tool invocation started, with human-readable status line
  - tool_result   → tool finished (no payload)
  - result        → final result with text, session_id, and usage metadata
  - error         → error with user-facing message (field is "text" in dicts)
  - stopped       → generation cancelled via /stop
  - silent        → process killed by signal (bot restart) — no user output

Consumer (handlers.py) accesses:
  - event["type"], event["text"], event["status"]
  - event.get("text", ""), event.get("usage"), event.get("cost"),
    event.get("num_turns"), event.get("duration_ms"), event.get("duration_api_ms")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class PartialEvent:
    """Streaming text delta (only emitted when verbose/streaming is on)."""
    type: Literal["partial"] = "partial"
    text: str = ""


@dataclass
class TextBlockEvent:
    """Complete text block from an AssistantMessage (before tool use or at end)."""
    type: Literal["text_block"] = "text_block"
    text: str = ""


@dataclass
class ToolUseEvent:
    """Tool invocation started. `status` is a human-readable status line."""
    type: Literal["tool_use"] = "tool_use"
    status: str = ""


@dataclass
class ToolResultEvent:
    """Tool execution completed. No payload — just a signal."""
    type: Literal["tool_result"] = "tool_result"


@dataclass
class ResultEvent:
    """Final result from Claude with text, session info, and usage metadata."""
    type: Literal["result"] = "result"
    text: str = ""
    session_id: str | None = None
    usage: Any = None  # SDK usage object or dict from subprocess JSON
    cost: float | None = None  # total_cost_usd
    num_turns: int | None = None
    duration_ms: int | None = None
    duration_api_ms: int | None = None


@dataclass
class ErrorEvent:
    """Error event. Note: the field is `text` (not `message`) to match existing dict usage."""
    type: Literal["error"] = "error"
    text: str = ""


@dataclass
class StoppedEvent:
    """Generation was cancelled via /stop."""
    type: Literal["stopped"] = "stopped"


@dataclass
class SilentEvent:
    """Process killed by signal (e.g. bot restart) — no user-visible output."""
    type: Literal["silent"] = "silent"


StreamEvent = (
    PartialEvent,
    TextBlockEvent,
    ToolUseEvent,
    ToolResultEvent,
    ResultEvent,
    ErrorEvent,
    StoppedEvent,
    SilentEvent
)
