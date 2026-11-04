"""SYNTHETIC tiny chest-X-ray-like dataset generator (smoke test only).

SYNTHETIC — not scientific results. Images are random blobs; nothing here resembles real radiographs
or real TB prevalence. Used only to prove the pipeline runs end to end.

  python -m tbml.synthetic --out data/synthetic/raw
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

BANNER = "SYNTHETIC — not scientific results"
INSTITUTIONS = {"inst_A": (0.0, 1.0), "inst_B": (15.0, 0.9), "inst_C": (-10.0, 1.1), "inst_EXT": (25.0, 0.7)}


def _image(rng, size: int, tb: bool, shift: float, gain: float) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size] / size
    img = 110 + 25 * rng.standard_normal((size, size)) * 0.4
    for cx in (0.3, 0.7):  # two darker "lung fields"
        img -= 45 * np.exp(-(((xx - cx) / 0.16) ** 2 + ((yy - 0.5) / 0.3) ** 2))
    if tb:  # bright upper-zone opacities
        for _ in range(rng.integers(1, 4)):
            cx, cy = rng.uniform(0.2, 0.8), rng.uniform(0.25, 0.5)
            img += 70 * np.exp(-(((xx - cx) / 0.07) ** 2 + ((yy - cy) / 0.07) ** 2))
    img = (img - 110) * gain + 110 + shift
    return np.clip(img, 0, 255).astype(np.uint8)


def generate(out: Path, seed: int = 0, size: int = 64, patients_per_inst=(30, 30, 30, 24)) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    if out.exists():
        shutil.rmtree(out)
    (out / "images").mkdir(parents=True)
    rows = []
    for (inst, (shift, gain)), n in zip(INSTITUTIONS.items(), patients_per_inst):
        for i in range(n):
            tb = bool(rng.random() < 0.4)
            for k in range(int(rng.integers(1, 3))):  # 1-2 images per patient (leakage risk is real)
                rel = f"images/{inst}_{i:03d}_{k}.png"
                Image.fromarray(_image(rng, size, tb, shift, gain)).save(out / rel)
                rows.append({"image_path": rel, "label": int(tb), "patient_id": f"{inst}-{i:03d}",
                             "institution": inst})
    # one exact duplicate file under another patient id, to exercise dedupe
    dup = rows[0]
    shutil.copy(out / dup["image_path"], out / "images/dup_of_first.png")
    rows.append({"image_path": "images/dup_of_first.png", "label": dup["label"],
                 "patient_id": "inst_A-dup", "institution": "inst_A"})
    df = pd.DataFrame(rows)
    df.to_csv(out / "manifest.csv", index=False)
    (out / "SYNTHETIC.txt").write_text(BANNER + "\n", encoding="utf-8")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/synthetic/raw"))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    d = generate(a.out, a.seed)
    print(f"{BANNER}: wrote {len(d)} images to {a.out}")
