"""Image normalization for the Anthropic API."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_IMAGE_DIM = 2048  # Anthropic recommended max dimension
_MAX_IMAGE_BYTES = 3 * 1024 * 1024  # 3MB raw limit (API encodes to base64)


def normalize_image(path: Path) -> Path:
    """Validate and normalize an image file for the Anthropic API.

    Re-saves as JPEG in RGB mode, resizes if too large.
    Returns the (possibly new) path on success, original path on failure.
    """
    try:
        from PIL import Image
        with Image.open(path) as img:
            # Convert to RGB (drops alpha channel, handles palette modes)
            if img.mode != "RGB":
                img = img.convert("RGB")
            # Resize if either dimension exceeds the limit
            if img.width > _MAX_IMAGE_DIM or img.height > _MAX_IMAGE_DIM:
                img.thumbnail((_MAX_IMAGE_DIM, _MAX_IMAGE_DIM), Image.LANCZOS)
            # Re-save as JPEG to ensure valid format
            new_path = path.with_suffix(".jpg")
            img.save(new_path, format="JPEG", quality=85, optimize=True)
            # If still too large, reduce quality further
            if new_path.stat().st_size > _MAX_IMAGE_BYTES:
                img.save(new_path, format="JPEG", quality=60, optimize=True)
            # Delete original only after new file is confirmed written
            if new_path != path:
                path.unlink(missing_ok=True)
            return new_path
    except Exception as e:
        logger.warning("Image normalization failed for %s: %s", path, e)
        return path
