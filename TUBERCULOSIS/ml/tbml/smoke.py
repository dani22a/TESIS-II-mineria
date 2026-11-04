"""End-to-end CPU smoke test on SYNTHETIC data: generate -> prep -> split -> train -> evaluate -> explain.

  python -m tbml.smoke [--models ...] [--trials 2] [--epochs 2]

SYNTHETIC — not scientific results. Passing proves the plumbing runs, nothing more.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from .models import MODEL_NAMES

BASE = Path("runs/smoke")


def sh(*args):
    print("\n$", "python -m", *args, flush=True)
    t = time.time()
    subprocess.run([sys.executable, "-m", *map(str, args)], check=True)
    print(f"[{time.time() - t:.0f}s]", flush=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap =argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=list(MODEL_NAMES))
    ap.add_argument("--trials", type=int, default=2)
    ap.add_argument("--epochs", type=int, default=2)
    a = ap.parse_args()
    raw, proc, run = BASE / "raw", BASE / "processed", BASE / "run"
    sh("tbml.synthetic", "--out", raw)
    sh("tbml.data_prep", "--layout", "manifest", "--raw", raw, "--out", proc, "--size", 64)
    sh("tbml.train", "--manifest", proc / "manifest.csv", "--out", run, "--models", *a.models,
       "--trials", a.trials, "--epochs", a.epochs, "--img-size", 64, "--external-institutions", "inst_EXT",
       "--mlflow")
    sh("tbml.evaluate", "--run", run, "--n-boot", 200)
    sh("tbml.explain", "--run", run, "--manifest", proc / "manifest.csv", "--n", 2)
    print("\nSYNTHETIC — not scientific results. Outputs in", run)


if __name__ == "__main__":
    main()
