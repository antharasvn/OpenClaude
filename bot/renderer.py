"""TelegramRenderer + message splitting."""

import html
import re

from bot.config import TELEGRAM_MAX_LENGTH


class TelegramRenderer:
    """Convert markdown-ish text to Telegram-compatible HTML."""

    @staticmethod
    def render(text: str) -> str:
        """Convert markdown to Telegram HTML.

        Handles: code blocks, inline code, bold, italic, strikethrough,
        headings (as bold), links, and lists.
        """
        # Protect code blocks first
        code_blocks: list[str] = []

        def _save_code_block(m: re.Match) -> str:
            lang = m.group(1) or ""
            code = html.escape(m.group(2))
            if lang:
                block = f'<pre><code class="language-{html.escape(lang)}">{code}</code></pre>'
            else:
                block = f"<pre>{code}</pre>"
            code_blocks.append(block)
            return f"\x00CODEBLOCK{len(code_blocks) - 1}\x00"

        text = re.sub(
            r"```(\w*)\n?(.*?)```", _save_code_block, text, flags=re.DOTALL
        )

        # Protect inline code
        inline_codes: list[str] = []

        def _save_inline_code(m: re.Match) -> str:
            code = html.escape(m.group(1))
            inline_codes.append(f"<code>{code}</code>")
            return f"\x00INLINECODE{len(inline_codes) - 1}\x00"

        text = re.sub(r"`([^`\n]+)`", _save_inline_code, text)

        # Escape HTML in the remaining text
        text = html.escape(text)

        # Headings -> bold
        text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

        # Bold: **text** or __text__
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

        # Italic: *text* or _text_
        text = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"<i>\1</i>", text)
        text = re.sub(r"(?<!\w)_([^_]+?)_(?!\w)", r"<i>\1</i>", text)

        # Strikethrough: ~~text~~
        text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

        # Links: [text](url)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

        # Unordered lists
        text = re.sub(r"^[\s]*[-*]\s+", "  \u2022 ", text, flags=re.MULTILINE)

        # Ordered lists
        text = re.sub(
            r"^[\s]*(\d+)\.\s+", r"  \1. ", text, flags=re.MULTILINE
        )

        # Restore code blocks and inline code
        for i, block in enumerate(code_blocks):
            text = text.replace(f"\x00CODEBLOCK{i}\x00", block)
        for i, code in enumerate(inline_codes):
            text = text.replace(f"\x00INLINECODE{i}\x00", code)

        return text.strip()


def _find_md_split(text: str, max_chars: int) -> int:
    """Find the best split point in markdown text within max_chars.

    Prefers: paragraph break > line break > sentence end > space.
    """
    if len(text) <= max_chars:
        return len(text)
    split_at = max_chars
    para = text.rfind("\n\n", 0, max_chars)
    if para > max_chars // 3:
        return para
    line = text.rfind("\n", 0, max_chars)
    if line > max_chars // 3:
        return line
    sent = text.rfind(". ", 0, max_chars)
    if sent > max_chars // 3:
        return sent + 1
    space = text.rfind(" ", 0, max_chars)
    if space > max_chars // 3:
        return space
    return split_at


def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """Split a markdown message into chunks that fit within Telegram's limit."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        split_at = _find_md_split(remaining, max_length)
        chunk = remaining[:split_at].rstrip()
        remaining = remaining[split_at:].lstrip()

        if chunk:
            chunks.append(chunk)

    return chunks


_MD_CHECK_THRESHOLD = 2500   # only render-check when markdown exceeds this
_HTML_SAFE_LIMIT = 3800      # split target — well under Telegram's 4096


def find_overflow_split(md_text: str, renderer) -> int | None:
    """Check if rendered HTML of md_text would exceed the safe limit.

    Returns the markdown split position if overflow detected, None otherwise.
    Uses a cheap length check first — only renders when markdown is long enough.
    """
    if len(md_text) <= _MD_CHECK_THRESHOLD:
        return None

    rendered = renderer.render(md_text)
    if len(rendered) <= _HTML_SAFE_LIMIT:
        return None

    # Binary search: find largest markdown prefix whose HTML fits in safe limit
    lo, hi = 0, len(md_text)
    best = hi // 2
    for _ in range(8):
        mid = (lo + hi) // 2
        split = _find_md_split(md_text, mid)
        if split <= lo:
            break
        test_html = renderer.render(md_text[:split])
        if len(test_html) <= _HTML_SAFE_LIMIT:
            best = split
            lo = split + 1
        else:
            hi = split
    return best
