"""File attachment parsing — extract image URLs, parse file markers, split segments."""

import logging
import os
import re

from bot.types import FileAttachment, FileSegment, Segment, TextSegment

logger = logging.getLogger(__name__)

# Image URL detection patterns
_IMAGE_EXTENSIONS = re.compile(r'\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s)]*)?$', re.IGNORECASE)
_MD_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_BARE_URL_RE = re.compile(
    r'(?<!\()(https?://\S+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s)]*)?)(?!\))',
    re.IGNORECASE,
)

# Local file attachment marker: 📎 /path/to/file [optional caption]
# Supports quoted paths for spaces: 📎 "/path/with spaces/file.pdf" caption
# Normalize pattern: join 📎 (with optional variation selector) split across lines
_FILE_MARKER_NORM = re.compile(r'📎\uFE0F?[ \t]*\n[ \t]*(?=["/])', re.MULTILINE)
_FILE_MARKER_RE = re.compile(r'^📎\uFE0F?[ \t]+(?:"([^"]+)"|(\S+))(?:[ \t]+(.+))?$', re.MULTILINE)
# Clean up stray 📎 left without a path (e.g. trailing marker)
_FILE_MARKER_STRAY = re.compile(r'^📎\uFE0F?[ \t]*$', re.MULTILINE)

_IMAGE_FILE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
_VIDEO_FILE_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
_AUDIO_FILE_EXTS = {'.mp3', '.ogg', '.wav', '.flac', '.aac', '.m4a', '.opus'}


def extract_image_urls(text: str) -> tuple[str, list[str]]:
    """Extract image URLs from markdown and return (cleaned_text, urls)."""
    urls: list[str] = []

    # Extract markdown images: ![alt](url)
    for match in _MD_IMAGE_RE.finditer(text):
        url = match.group(2)
        if _IMAGE_EXTENSIONS.search(url):
            urls.append(url)

    # Remove markdown image syntax for extracted images
    cleaned = _MD_IMAGE_RE.sub(
        lambda m: '' if _IMAGE_EXTENSIONS.search(m.group(2)) else m.group(0),
        text,
    )

    # Extract bare image URLs (not already captured in markdown syntax)
    for match in _BARE_URL_RE.finditer(cleaned):
        url = match.group(1)
        if url not in urls:
            urls.append(url)

    # Remove bare image URLs from text
    if urls:
        cleaned = _BARE_URL_RE.sub(
            lambda m: '' if m.group(1) in urls else m.group(0),
            cleaned,
        )

    # Clean up leftover blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()

    return cleaned, urls


def split_file_segments(text: str, workspace: str) -> list[Segment]:
    """Split text into ordered segments of text and file groups.

    Returns a list of TextSegment and FileSegment objects.
    Consecutive 📎 lines are grouped together so they can be sent as a media group.
    Only files within the workspace directory are accepted.
    """
    # Normalize: join 📎 split across lines into single-line form
    text = _FILE_MARKER_NORM.sub('\U0001f4ce ', text)

    ws_real = os.path.realpath(workspace)
    segments: list[Segment] = []
    last_end = 0
    pending_files: list[FileAttachment] = []

    for match in _FILE_MARKER_RE.finditer(text):
        # Text between previous match and this one
        gap = text[last_end:match.start()]
        gap_clean = _FILE_MARKER_STRAY.sub('', gap).strip()

        # If there's real text between file markers, flush pending files first
        if gap_clean and pending_files:
            segments.append(FileSegment(files=pending_files))
            pending_files = []
        if gap_clean:
            segments.append(TextSegment(content=gap_clean))

        raw_path = match.group(1) or match.group(2)
        caption = (match.group(3) or "").strip()
        real_path = os.path.realpath(raw_path)

        # Security: must be within workspace
        if not real_path.startswith(ws_real + os.sep) and real_path != ws_real:
            logger.warning("\U0001f4ce path outside workspace, skipping: %s", raw_path)
            last_end = match.end()
            continue

        if not os.path.isfile(real_path):
            logger.warning("\U0001f4ce file not found, skipping: %s", raw_path)
            last_end = match.end()
            continue

        ext = os.path.splitext(real_path)[1].lower()
        if ext in _IMAGE_FILE_EXTS:
            media_type = "photo"
        elif ext in _VIDEO_FILE_EXTS:
            media_type = "video"
        elif ext in _AUDIO_FILE_EXTS:
            media_type = "audio"
        else:
            media_type = "document"

        pending_files.append(FileAttachment(path=real_path, caption=caption, media_type=media_type))
        last_end = match.end()

    # Flush remaining pending files
    if pending_files:
        segments.append(FileSegment(files=pending_files))

    # Trailing text after the last match
    tail = text[last_end:]
    tail = _FILE_MARKER_STRAY.sub('', tail)
    tail = re.sub(r'\n{3,}', '\n\n', tail).strip()
    if tail:
        segments.append(TextSegment(content=tail))

    return segments


def clean_file_markers(text: str) -> str:
    """Remove 📎 marker lines from text for display purposes."""
    text = _FILE_MARKER_NORM.sub('\U0001f4ce ', text)
    text = _FILE_MARKER_RE.sub('', text)
    text = _FILE_MARKER_STRAY.sub('', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()
