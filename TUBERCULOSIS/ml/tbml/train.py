"""Training with Optuna (TPE + pruner). Threshold and calibration come from the VALIDATION split only.

  python -m tbml.train --manifest data/processed/synthetic/manifest.csv --out runs/smoke \
      --models densenet121 vit --trials 2 --epochs 2 --img-size 64 --external-institutions inst_EXT
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import optuna
import pandas as pd
import torch
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from torch import nn

from .models import MODEL_NAMES, get_model
from .splits import split_manifest
from .tracking import Tracker

optuna.logging.set_verbosity(optuna.logging.WARNING)


def load_tensors(df: pd.DataFrame, root: Path, size: int):
    xs = [np.asarray(Image.open(root / p).convert("L").resize((size, size)), dtype=np.float32) / 255.0
          for p in df["image_path"]]
    x = torch.from_numpy(np.stack(xs))[:, None]
    return (x - 0.5) / 0.5, torch.tensor(df["label"].values, dtype=torch.float32)


@torch.no_grad()
def predict_logits(model, x, device, bs=32) -> np.ndarray:
    model.eval()
    return np.concatenate([model(x[i:i + bs].to(device)).cpu().numpy() for i in range(0, len(x), bs)])


def train_one(name, params, data, epochs, device, seed, ckpt: Path, trial=None, model_kw=None) -> float:
    """Train; keep the best-validation-AUC epoch checkpoint. Returns best validation AUC."""
    torch.manual_seed(seed)
    xtr, ytr, xva, yva = data
    model = get_model(name, img_size=xtr.shape[-1], dropout=params["dropout"], **(model_kw or {})).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=params["lr"], weight_decay=params["weight_decay"])
    pos_w = ((len(ytr) - ytr.sum()) / ytr.sum().clamp(min=1)).to(device)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_w)
    bs, n, best = params["batch_size"], len(xtr), -1.0
    g = torch.Generator().manual_seed(seed)
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            if len(idx) < 2:  # BatchNorm needs >1 sample
                continue
            opt.zero_grad()
            loss_fn(model(xtr[idx].to(device)), ytr[idx].to(device)).backward()
            opt.step()
        auc = roc_auc_score(yva.numpy(), predict_logits(model, xva, device))
        if auc > best:
            best = auc
            torch.save(model.state_dict(), ckpt)
        if trial is not None:
            trial.report(auc, ep)
            if trial.should_prune():
                raise optuna.TrialPruned()
    return best


def choose_threshold(y, p, target_sensitivity: float | None = None) -> float:
    """Youden J on dev data, or the highest threshold reaching the target sensitivity (screening)."""
    fpr, tpr, thr = roc_curve(y, p)
    keep = np.isfinite(thr)  # drop the sentinel "predict nothing" point (inf)
    fpr, tpr, thr = fpr[keep], tpr[keep], thr[keep]
    if len(thr) == 0:
        return 0.5
    if target_sensitivity is not None:
        ok = np.where(tpr >= target_sensitivity)[0]
        return float(thr[ok[0]]) if len(ok) else float(thr[-1])
    return float(thr[np.argmax(tpr - fpr)])


def fit_calibration(logits, y) -> dict:
    """Platt scaling fitted on validation logits only."""
    lr = LogisticRegression(C=1e6).fit(np.asarray(logits).reshape(-1, 1), y)
    return {"a": float(lr.coef_[0, 0]), "b": float(lr.intercept_[0])}


def apply_calibration(logits, cal) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-(cal["a"] * np.asarray(logits) + cal["b"])))


def run_model(name, splits, root, out: Path, img_size, trials, epochs, seed, device, tracker,
              target_sensitivity=None, model_kw=None) -> dict:
    mdir = out / name
    mdir.mkdir(parents=True, exist_ok=True)
    tens = {k: load_tensors(v, root, img_size) for k, v in splits.items()}
    data = (*tens["train"], *tens["val"])

    def objective(trial):
        params = {"lr": trial.suggest_float("lr", 1e-5, 3e-3, log=True),
                  "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-2, log=True),
                  "batch_size": trial.suggest_categorical("batch_size", [8, 16, 32]),
                  "dropout": trial.suggest_float("dropout", 0.0, 0.5)}
        return train_one(name, params, data, epochs, device, seed, mdir / f"trial_{trial.number}.pt",
                         trial, model_kw)

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed),
                                pruner=optuna.pruners.MedianPruner(n_startup_trials=1, n_warmup_steps=0))
    study.optimize(objective, n_trials=trials)
    done = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    if not done:
        raise RuntimeError(f"{name}: all trials were pruned/failed")
    best = max(done, key=lambda t: t.value)
    shutil.copy(mdir / f"trial_{best.number}.pt", mdir / "model.pt")
    for f in mdir.glob("trial_*.pt"):
        f.unlink()

    model = get_model(name, img_size=img_size, dropout=best.params["dropout"], **(model_kw or {})).to(device)
    model.load_state_dict(torch.load(mdir / "model.pt", map_location=device))
    logits = {k: predict_logits(model, tens[k][0], device) for k in splits}
    yv = splits["val"]["label"].values
    cal = fit_calibration(logits["val"], yv)  # dev (validation) data only
    thr = choose_threshold(yv, apply_calibration(logits["val"], cal), target_sensitivity)
    synthetic = bool(splits["train"].get("synthetic", pd.Series([False])).any())
    notice = "SYNTHETIC — not scientific results" if synthetic else None
    for k, df in splits.items():
        o = df[["image_id", "patient_id", "institution", "label"]].rename(columns={"label": "y_true"}).copy()
        o["logit"] = logits[k]
        o["prob"] = apply_calibration(logits[k], cal)
        o.to_csv(mdir / f"preds_{k}.csv", index=False)
    meta = {"model": name, "img_size": img_size, "best_params": best.params, "best_val_auc": best.value,
            "threshold": thr, "threshold_source": "validation", "calibration": {"method": "platt", **cal,
            "fit_on": "validation"}, "target_sensitivity": target_sensitivity, "model_kw": model_kw or {},
            "trials": {"requested": trials, "completed": len(done),
                       "pruned": sum(t.state == optuna.trial.TrialState.PRUNED for t in study.trials)},
            "epochs": epochs, "seed": seed, "notice": notice}
    (mdir / "calibration.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    with tracker.run(name):
        tracker.params({**best.params, "model": name, "epochs": epochs})
        tracker.metrics({"best_val_auc": best.value, "threshold": thr})
        tracker.artifact(mdir / "calibration.json")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--models", nargs="+", default=list(MODEL_NAMES), choices=MODEL_NAMES)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--img-size", type=int, default=224)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--group-col", default="patient_id")
    ap.add_argument("--external-institutions", nargs="*", default=[])
    ap.add_argument("--target-sensitivity", type=float, default=None)
    ap.add_argument("--mlflow", action="store_true", help="log to MLflow if installed")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()
    df = pd.read_csv(a.manifest)
    root = a.manifest.parent
    splits = split_manifest(df, a.group_col, seed=a.seed, external_institutions=tuple(a.external_institutions))
    a.out.mkdir(parents=True, exist_ok=True)
    pd.concat([v.assign(split=k) for k, v in splits.items()]).to_csv(a.out / "splits.csv", index=False)
    tracker = Tracker(a.mlflow)
    for m in a.models:
        meta = run_model(m, splits, root, a.out, a.img_size, a.trials, a.epochs, a.seed, a.device, tracker,
                         a.target_sensitivity)
        print(f"{m}: best_val_auc={meta['best_val_auc']:.3f} threshold={meta['threshold']:.3f} "
              f"trials={meta['trials']}")


if __name__ == "__main__":
    main()
