"""Typed data structures for the handlers layer."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class FileAttachment:
    """A local file to be sent via Telegram."""
    path: str
    caption: str = ""
    media_type: Literal["photo", "video", "audio", "document"] = "document"


@dataclass
class TextSegment:
    """A segment of plain text in a response."""
    content: str


@dataclass
class FileSegment:
    """A group of consecutive file attachments in a response."""
    files: list[FileAttachment]


Segment = TextSegment | FileSegment
