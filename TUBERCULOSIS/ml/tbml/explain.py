"""Explainability: Grad-CAM for CNN-based models, attention rollout for the ViT.

  python -m tbml.explain --run runs/smoke --manifest data/processed/synthetic/manifest.csv --n 3
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw

from .models import get_model
from .train import load_tensors


def gradcam(model, x: torch.Tensor) -> np.ndarray:
    """x: (1,1,H,W). Returns heatmap (H,W) in [0,1] for the positive-class logit."""
    store = {}
    layer = model.cam_layer

    def fwd(_, __, out):
        store["a"] = out
        out.register_hook(lambda g: store.__setitem__("g", g))

    h = layer.register_forward_hook(fwd)
    try:
        model.eval()
        model.zero_grad()
        model(x).sum().backward()
    finally:
        h.remove()
    w = store["g"].mean(dim=(2, 3), keepdim=True)
    cam = F.relu((w * store["a"]).sum(1, keepdim=True))
    cam = F.interpolate(cam, size=x.shape[-2:], mode="bilinear", align_corners=False)[0, 0].detach().numpy()
    return (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)


@torch.no_grad()
def attention_rollout(model, x: torch.Tensor) -> np.ndarray:
    model.eval()
    model(x)
    r = None
    for blk in model.blocks:
        a = blk.attn.last_attn.mean(1)[0]  # head-averaged (T, T)
        a = a + torch.eye(a.shape[0])
        a = a / a.sum(-1, keepdim=True)
        r = a if r is None else a @ r
    g = model.grid
    m = r[0, 1:].reshape(1, 1, g, g)  # CLS -> patches
    m = F.interpolate(m, size=x.shape[-2:], mode="bilinear", align_corners=False)[0, 0].numpy()
    return (m - m.min()) / (m.max() - m.min() + 1e-8)


def overlay(gray: np.ndarray, heat: np.ndarray, stamp: str | None) -> Image.Image:
    g = ((gray * 0.5 + 0.5).clip(0, 1) * 255).astype(np.uint8)
    rgb = np.stack([g] * 3, -1).astype(np.float32)
    red = np.zeros_like(rgb)
    red[..., 0] = 255
    a = (heat[..., None] * 0.55).astype(np.float32)
    img = Image.fromarray((rgb * (1 - a) + red * a).astype(np.uint8)).resize((256, 256))
    if stamp:
        ImageDraw.Draw(img).text((4, 4), stamp, fill=(255, 255, 0))
    return img


def explain_run(run: Path, manifest: Path, split: str = "test", n: int = 3) -> list[Path]:
    df = pd.read_csv(run / "splits.csv")
    df = df[df.split == split].head(n)
    mf = pd.read_csv(manifest)
    root = manifest.parent
    written = []
    for mdir in sorted(p for p in run.iterdir() if (p / "calibration.json").exists()):
        meta = json.loads((mdir / "calibration.json").read_text(encoding="utf-8"))
        model = get_model(meta["model"], img_size=meta["img_size"], dropout=meta["best_params"]["dropout"],
                          **meta.get("model_kw", {}))
        model.load_state_dict(torch.load(mdir / "model.pt", map_location="cpu"))
        xs, _ = load_tensors(df, root, meta["img_size"])
        stamp = "SYNTHETIC - not scientific results" if meta.get("notice") else None
        out = run / "explain" / mdir.name
        out.mkdir(parents=True, exist_ok=True)
        for i, row in enumerate(df.itertuples()):
            x = xs[i:i + 1]
            heat = attention_rollout(model, x) if meta["model"] == "vit" else gradcam(model, x)
            p = out / f"{row.image_id}.png"
            overlay(x[0, 0].numpy(), heat, stamp).save(p)
            written.append(p)
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    for p in explain_run(a.run, a.manifest, a.split, a.n):
        print(p)


if __name__ == "__main__":
    main()
