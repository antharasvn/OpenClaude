"""LaTeX math rendering — extract LaTeX blocks from text and render them as PNG.

Uses KaTeX rendered via pinchtab (headless Chrome) for high-quality output.
Falls back to matplotlib mathtext if pinchtab is unavailable.
"""

import base64
import json
import logging
import os
import re
import subprocess
import tempfile
import time

logger = logging.getLogger(__name__)

# Display math: $$...$$  (multiline)
_DISPLAY_RE = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)

# Inline math: $...$  (single-line, not preceded/followed by another $)
_INLINE_RE = re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)')

# Trivial expressions to skip (pure numbers, very short, prices)
_PRICE_RE = re.compile(r'^\d[\d,. ]*$')

# Structural LaTeX commands that indicate real complexity
_STRUCTURAL_CMDS = (
    r'\frac', r'\sum', r'\int', r'\prod', r'\lim', r'\binom',
    r'\begin', r'\sqrt', r'\left', r'\right', r'\over',
    r'\underbrace', r'\overbrace', r'\partial', r'\nabla',
    r'\oint', r'\iint', r'\iiint', r'\bigcup', r'\bigcap',
)

def _complexity_score(expr: str) -> int:
    """Score formula complexity. Higher = more worth rendering."""
    score = 0
    for cmd in _STRUCTURAL_CMDS:
        score += expr.count(cmd) * 3
    score += expr.count('_')
    score += expr.count('^')
    score += expr.count('{') // 2
    return score


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


_COMPLEXITY_THRESHOLD = 3

def _should_skip(expr: str, min_length: int = 4) -> bool:
    """Return True if the expression is trivial and should not be rendered."""
    if len(expr) < min_length:
        return True
    if _PRICE_RE.match(expr):
        return True
    if _complexity_score(expr) < _COMPLEXITY_THRESHOLD:
        return True
    return False


def _find_pinchtab_port() -> int | None:
    """Discover the pinchtab HTTP API port from listening sockets."""
    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "pinchtab" in line:
                # Extract port from  127.0.0.1:NNNNN  or  *:NNNNN
                for part in line.split():
                    if ":" in part and not part.startswith("users"):
                        port_str = part.rsplit(":", 1)[-1]
                        if port_str.isdigit():
                            return int(port_str)
    except Exception:
        pass
    return None


def _autocrop_png(path: str) -> bool:
    """Crop whitespace from a PNG, leaving a small padding."""
    try:
        from PIL import Image, ImageChops

        img = Image.open(path).convert("RGB")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if not bbox:
            return False
        # Add padding
        pad = 20
        x0 = max(0, bbox[0] - pad)
        y0 = max(0, bbox[1] - pad)
        x1 = min(img.width, bbox[2] + pad)
        y1 = min(img.height, bbox[3] + pad)
        cropped = img.crop((x0, y0, x1, y1))
        cropped.save(path)
        return True
    except Exception:
        logger.debug("Autocrop failed for %s", path, exc_info=True)
        return False


def render_latex_png(expression: str, output_path: str, display: bool = True) -> bool:
    """Render a LaTeX expression to PNG using KaTeX via pinchtab.

    Falls back to matplotlib mathtext if pinchtab is unavailable.

    Args:
        expression: LaTeX math expression (without $ delimiters).
        output_path: Path for the output PNG file.
        display: If True, use display math mode (larger, centered).

    Returns:
        True on success, False if the expression could not be rendered.
    """
    if _render_katex(expression, output_path, display):
        return True
    logger.debug("KaTeX unavailable, falling back to matplotlib for: %s", expression)
    return _render_matplotlib(expression, output_path, display)


def _render_katex(expression: str, output_path: str, display: bool = True) -> bool:
    """Render LaTeX via KaTeX + pinchtab headless Chrome."""
    port = _find_pinchtab_port()
    if port is None:
        return False

    base_url = f"http://localhost:{port}"

    try:
        display_str = "true" if display else "false"
        # Escape for JS template literal
        js_expr = (expression
                   .replace("\\", "\\\\")
                   .replace("`", "\\`")
                   .replace("$", "\\$"))

        html = f"""<!DOCTYPE html>
<html><head>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: white; }}
#math {{ padding: 20px 30px; font-size: 22px; display: inline-block; }}
</style>
</head><body>
<div id="math"></div>
<script>
try {{
  katex.render(`{js_expr}`, document.getElementById('math'),
    {{displayMode: {display_str}, throwOnError: false}});
}} catch(e) {{
  document.getElementById('math').textContent = 'Error: ' + e.message;
}}
</script>
</body></html>"""

        # Use data URI to avoid file:// restrictions in sandboxed Chrome
        b64 = base64.b64encode(html.encode()).decode()
        data_url = f"data:text/html;base64,{b64}"

        nav_payload = json.dumps({"url": data_url})
        subprocess.run(
            ["curl", "-s", "-X", "POST", f"{base_url}/navigate",
             "-H", "Content-Type: application/json", "-d", nav_payload],
            timeout=10, capture_output=True, check=True,
        )
        time.sleep(2.5)  # Wait for KaTeX CDN + JS render

        # Take screenshot
        result = subprocess.run(
            ["curl", "-s", f"{base_url}/screenshot"],
            timeout=15, capture_output=True, check=True,
        )
        if len(result.stdout) < 1000:
            logger.debug("KaTeX screenshot too small (%d bytes)", len(result.stdout))
            return False

        with open(output_path, "wb") as f:
            f.write(result.stdout)

        # Crop whitespace
        _autocrop_png(output_path)

        return True

    except Exception:
        logger.debug("KaTeX render failed: %s", expression, exc_info=True)
        return False


def _render_matplotlib(expression: str, output_path: str, display: bool = True) -> bool:
    """Render LaTeX via matplotlib mathtext (fallback)."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fontsize = 24 if display else 18
        dpi = 150

        fig = plt.figure(figsize=(0.01, 0.01))
        fig.patch.set_facecolor('white')

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
        logger.debug("Matplotlib render failed: %s", expression, exc_info=True)
        try:
            plt.close(fig)  # noqa: F821
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
