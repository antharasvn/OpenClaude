"""LaTeX math rendering — extract LaTeX blocks from text and render them as PNG.

Uses matplotlib's mathtext engine for rendering (no external LaTeX installation needed).
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

# Display math: $$...$$  (multiline)
_DISPLAY_RE = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)

# Inline math: $...$  (single-line, not preceded/followed by another $)
_INLINE_RE = re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)')

# Trivial expressions to skip (pure numbers, very short, prices)
_PRICE_RE = re.compile(r'^\d[\d,. ]*$')


def extract_latex_blocks(text: str, min_length: int = 4) -> list[tuple[str, str]]:
    """Extract LaTeX math expressions from text.

    Returns a list of (expression, mode) tuples where mode is
    "display" ($$...$$) or "inline" ($...$).

    Deduplicates by expression text. Skips trivial matches
    (pure numbers, very short strings, price-like patterns).

    Args:
        text: Source text containing LaTeX math expressions.
        min_length: Minimum length of the expression (excluding $ delimiters)
            to be included. Expressions shorter than this are considered
            trivial and skipped. Default: 4.
    """
    seen: set[str] = set()
    results: list[tuple[str, str]] = []

    # Display math first (greedy priority over inline)
    for m in _DISPLAY_RE.finditer(text):
        expr = m.group(1).strip()
        if _should_skip(expr, min_length):
            continue
        if expr not in seen:
            seen.add(expr)
            results.append((expr, "display"))

    # Remove display blocks from text before scanning for inline
    text_no_display = _DISPLAY_RE.sub('', text)

    for m in _INLINE_RE.finditer(text_no_display):
        expr = m.group(1).strip()
        if _should_skip(expr, min_length):
            continue
        if expr not in seen:
            seen.add(expr)
            results.append((expr, "inline"))

    return results


def _should_skip(expr: str, min_length: int = 4) -> bool:
    """Return True if the expression is trivial and should not be rendered."""
    if len(expr) < min_length:
        return True
    if _PRICE_RE.match(expr):
        return True
    return False


def render_latex_png(expression: str, output_path: str, display: bool = True) -> bool:
    """Render a LaTeX expression to a PNG file using matplotlib mathtext.

    Args:
        expression: LaTeX math expression (without $ delimiters).
        output_path: Path for the output PNG file.
        display: If True, use larger font (display math style).

    Returns:
        True on success, False if the expression could not be rendered.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib import mathtext

        fontsize = 24 if display else 18
        dpi = 150

        fig = plt.figure(figsize=(0.01, 0.01))
        fig.patch.set_facecolor('white')

        # Wrap in $ for mathtext
        fig.text(
            0.5, 0.5,
            f'${expression}$',
            fontsize=fontsize,
            ha='center',
            va='center',
        )

        fig.savefig(
            output_path,
            dpi=dpi,
            bbox_inches='tight',
            pad_inches=0.3,
            facecolor='white',
            edgecolor='none',
        )
        plt.close(fig)
        return True

    except Exception:
        logger.debug("Failed to render LaTeX: %s", expression, exc_info=True)
        try:
            plt.close(fig)
        except Exception:
            pass
        return False


def render_all_latex(text: str, output_dir: str) -> list[str]:
    """Extract and render all LaTeX blocks from text.

    Args:
        text: Source text containing LaTeX math expressions.
        output_dir: Directory for output PNG files (created if needed).

    Returns:
        List of paths to successfully rendered PNG files.
    """
    blocks = extract_latex_blocks(text)
    if not blocks:
        return []

    os.makedirs(output_dir, exist_ok=True)

    paths: list[str] = []
    for i, (expr, mode) in enumerate(blocks):
        out_path = os.path.join(output_dir, f"latex_{i}.png")
        is_display = mode == "display"
        if render_latex_png(expr, out_path, display=is_display):
            paths.append(out_path)

    return paths
