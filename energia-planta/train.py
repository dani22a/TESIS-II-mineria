"""Headless end-to-end training: preparation -> search -> freeze -> exam -> stats -> SHAP -> export.

Usage:
    python train.py                 # full run (search included, ~1-2 minutes)
    python train.py --reuse-search  # reuse artefactos/hiperparametros_congelados.json
"""
import argparse
import json
import sys
import time

from lab import pipeline
from lab.config import FINAL_ARTIFACT, MODELS


def main() -> int:
    parser = argparse.ArgumentParser(description="Train, evaluate and export the plant energy model.")
    parser.add_argument("--reuse-search", action="store_true", help="skip the hyperparameter search if frozen values exist")
    args = parser.parse_args()

    t0 = time.time()
    artifact = pipeline.run_all(
        progress=lambda msg, frac: print(f"[{frac:5.0%}] {msg}", flush=True),
        reuse_search=args.reuse_search,
    )
    per = artifact["exam_metrics"]["per_model"]
    print("\nExam metrics (Oct-Dec 2018):")
    for m in MODELS:
        v = per[m]
        print(f"  {m:14s} MAE {v['mae']:.3f}  RMSE {v['rmse']:.3f}  MAPE {v['mape']:.1f} %  R2 {v['r2']:.3f}")
    s = artifact["stats_summary"]
    fr = s["friedman_weekly_mae"]
    print(f"\nFriedman ({fr['n_windows']} weekly windows): chi2 {fr['chi2']:.2f}, p {fr['p']:.4g}, mean ranks {json.dumps(fr['mean_ranks'])}")
    for r in s["diebold_mariano_december_abs_error"]:
        print(f"DM December {r['a']} vs {r['b']}: stat {r['stat']:.2f}, p {r['p_nw']:.4g} (p lag96 {r['p_lag96']:.4g})")
    print(f"\nExported model: {artifact['model']} -> {FINAL_ARTIFACT}  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
