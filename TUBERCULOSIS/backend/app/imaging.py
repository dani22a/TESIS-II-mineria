"""Upload validation and quality control."""
import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, UnidentifiedImageError

from .config import settings

Image.MAX_IMAGE_PIXELS = 40_000_000

MAGIC = {"png": b"\x89PNG\r\n\x1a\n", "jpeg": b"\xff\xd8\xff"}
MIME = {"image/png": "png", "image/jpeg": "jpeg"}


class InvalidUpload(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


@dataclass
class QCResult:
    passed: bool
    reason: str | None
    width: int
    height: int


def validate_upload(data: bytes, content_type: str | None) -> str:
    """Return the real format or raise InvalidUpload. Checks size, magic bytes and MIME agreement."""
    if not data:
        raise InvalidUpload(400, "Empty file")
    if len(data) > settings.max_upload_bytes:
        raise InvalidUpload(413, "File too large")
    fmt = next((f for f, m in MAGIC.items() if data.startswith(m)), None)
    if fmt is None:
        raise InvalidUpload(415, "Unsupported file type (only PNG or JPEG)")
    if MIME.get((content_type or "").lower()) != fmt:
        raise InvalidUpload(415, "Declared content type does not match file content")
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise InvalidUpload(422, "Corrupt or unreadable image")
    return fmt


def quality_control(data: bytes) -> QCResult:
    with Image.open(io.BytesIO(data)) as img:
        w, h = img.size
        gray = np.asarray(img.convert("L"), dtype=np.float32)
    if min(w, h) < settings.min_image_side:
        return QCResult(False, f"resolution below {settings.min_image_side}px", w, h)
    if float(gray.std()) < settings.min_pixel_std:
        return QCResult(False, "blank or uniform image", w, h)
    return QCResult(True, None, w, h)
