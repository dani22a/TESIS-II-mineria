"""Data preparation: dedupe by hash, intensity normalization, lung-segmentation hook, QC.

Output: <out>/images/*.png (8-bit grayscale, square), <out>/manifest.csv, <out>/prep_report.json.
Manifest columns: image_id, image_path (relative to out), label, patient_id, institution, sha256, synthetic.

  python -m tbml.data_prep --layout shenzhen --raw /data/ChinaSet --out data/processed/shenzhen --size 224
  python -m tbml.data_prep --layout manifest --raw data/synthetic/raw --out data/processed/synthetic
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd
from PIL import Image


class LungSegmenter(Protocol):
    def segment(self, img: np.ndarray) -> np.ndarray:
        """float image (H, W) in [0, 1] -> bool mask (H, W), True inside the lung fields."""


class FullImageSegmenter:
    """PLACEHOLDER: no segmentation, the whole image is 'lung'. Plug a real model (e.g. a U-Net
    trained on Montgomery/Shenzhen masks) implementing LungSegmenter and pass it to prepare()."""

    def segment(self, img: np.ndarray) -> np.ndarray:
        return np.ones(img.shape, dtype=bool)


def scan_shenzhen(raw: Path) -> pd.DataFrame:
    """Shenzhen (CHNCXR_####_{0,1}.png) and Montgomery (MCUCXR_####_{0,1}.png); suffix 0=normal, 1=TB.
    Place both under `raw` (any depth). Montgomery is a separate institution: a natural external set."""
    rows = []
    for p in sorted(raw.rglob("*.png")):
        m = re.match(r"(CHNCXR|MCUCXR)_(\d+)_([01])\.png$", p.name)
        if not m:
            continue
        inst = "shenzhen" if m.group(1) == "CHNCXR" else "montgomery"
        rows.append({"image_path": str(p.relative_to(raw)), "label": int(m.group(3)),
                     "patient_id": f"{inst}-{m.group(2)}", "institution": inst})
    return pd.DataFrame(rows)


def normalize(img: np.ndarray, mask: np.ndarray, size: int) -> np.ndarray:
    """Clip to the 1st-99th percentile inside the mask, scale to [0,1], resize to size x size, uint8."""
    region = img[mask] if mask.any() else img.ravel()
    lo, hi = np.percentile(region, [1, 99])
    x = np.clip((img - lo) / max(hi - lo, 1e-6), 0, 1)
    out = Image.fromarray((x * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR)
    return np.asarray(out)


def qc_reason(img: np.ndarray, min_side: int, min_std: float) -> str | None:
    h, w = img.shape
    if min(h, w) < min_side:
        return f"too_small({w}x{h})"
    if img.std() < min_std:
        return "low_contrast"
    return None


def prepare(manifest: pd.DataFrame, raw: Path, out: Path, size: int = 224, min_side: int = 64,
            min_std: float = 4.0, segmenter: LungSegmenter | None = None, synthetic: bool = False) -> dict:
    segmenter = segmenter or FullImageSegmenter()
    (out / "images").mkdir(parents=True, exist_ok=True)
    kept, dropped = [], []
    seen: dict[str, tuple[int, str]] = {}  # raw-bytes hash -> (label, image_path)
    for r in manifest.itertuples():
        path = raw / r.image_path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            dropped.append({"image_path": r.image_path, "reason": "duplicate",
                            "of": seen[digest][1], "label_conflict": seen[digest][0] != r.label})
            continue
        seen[digest] = (r.label, r.image_path)
        img = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
        why = qc_reason(img, min_side, min_std)
        if why:
            dropped.append({"image_path": r.image_path, "reason": why})
            continue
        mask = segmenter.segment(img / 255.0)
        arr = normalize(img, mask, size)
        image_id = f"{r.patient_id}_{digest[:8]}"
        rel = f"images/{image_id}.png"
        Image.fromarray(arr).save(out / rel)
        kept.append({"image_id": image_id, "image_path": rel, "label": int(r.label),
                     "patient_id": r.patient_id, "institution": r.institution,
                     "sha256": digest, "synthetic": synthetic})
    mf = pd.DataFrame(kept)
    mf.to_csv(out / "manifest.csv", index=False)
    conflicts = [d for d in dropped if d.get("label_conflict")]
    report = {"input_images": len(manifest), "kept": len(kept), "dropped": len(dropped),
              "dropped_detail": dropped, "duplicate_label_conflicts": len(conflicts),
              "size": size, "segmenter": type(segmenter).__name__,
              "segmentation_is_placeholder": isinstance(segmenter, FullImageSegmenter),
              "synthetic": synthetic,
              "notice": "SYNTHETIC — not scientific results" if synthetic else None}
    (out / "prep_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", choices=["shenzhen", "manifest"], required=True)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--min-side", type=int, default=64)
    a = ap.parse_args()
    synthetic = (a.raw / "SYNTHETIC.txt").exists()
    mf = scan_shenzhen(a.raw) if a.layout == "shenzhen" else pd.read_csv(a.raw / "manifest.csv")
    rep = prepare(mf, a.raw, a.out, a.size, a.min_side, synthetic=synthetic)
    print(json.dumps({k: v for k, v in rep.items() if k != "dropped_detail"}, indent=2))


if __name__ == "__main__":
    main()
