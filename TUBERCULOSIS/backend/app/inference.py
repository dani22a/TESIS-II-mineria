"""Inference engines. The default engine is a DEMO: it is NOT a clinical model."""
import abc
import hashlib
import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

LABEL_TB = "probable_tuberculosis"
LABEL_NEG = "no_compatible_findings"


@dataclass
class Prediction:
    score: float
    heatmap_png: bytes | None = None


class InferenceEngine(abc.ABC):
    model_version: str
    is_demo: bool

    @abc.abstractmethod
    def predict(self, image_bytes: bytes) -> Prediction: ...


class DemoEngine(InferenceEngine):
    """Deterministic pseudo-score from the image hash plus a synthetic overlay. Not a diagnosis."""

    model_version = "demo-0"
    is_demo = True

    def predict(self, image_bytes: bytes) -> Prediction:
        digest = hashlib.sha256(image_bytes).digest()
        score = int.from_bytes(digest[:8], "big") / 2**64
        return Prediction(score=score, heatmap_png=self._overlay(image_bytes, digest))

    @staticmethod
    def _overlay(image_bytes: bytes, digest: bytes) -> bytes:
        size = 256
        with Image.open(io.BytesIO(image_bytes)) as img:
            base = img.convert("L").resize((size, size)).convert("RGB")
        cx, cy = 64 + digest[8] % 128, 64 + digest[9] % 128
        yy, xx = np.mgrid[0:size, 0:size]
        blob = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 40.0**2)))
        arr = np.asarray(base, dtype=np.float32)
        arr[..., 0] = np.clip(arr[..., 0] + 160 * blob, 0, 255)
        arr[..., 1] *= 1 - 0.5 * blob
        arr[..., 2] *= 1 - 0.5 * blob
        out = Image.fromarray(arr.astype(np.uint8))
        ImageDraw.Draw(out).text((6, 6), "DEMO - not a clinical result", fill=(255, 255, 0))
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        return buf.getvalue()


def get_engine() -> InferenceEngine:
    return DemoEngine()
