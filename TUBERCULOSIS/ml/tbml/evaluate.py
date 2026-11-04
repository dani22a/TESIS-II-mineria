"""Evaluate trained runs on held-out splits (test, external). Thresholds/calibration are read from the
dev-only calibration.json; nothing is refit here.

  python -m tbml.evaluate --run runs/smoke [--cv-metrics cv_metrics.csv] [--n-boot 500]
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import pandas as pd

from . import metrics as M

BANNER = "SYNTHETIC — not scientific results"
KEY = ("sensitivity", "specificity", "f1", "mcc", "auc_roc", "auc_pr")


def load_run(run: Path) -> dict:
    out = {}
    for d in sorted(p for p in run.iterdir() if (p / "calibration.json").exists()):
        meta = json.loads((d / "calibration.json").read_text(encoding="utf-8"))
        out[d.name] = {"meta": meta, **{s: pd.read_csv(d / f"preds_{s}.csv")
                                        for s in ("val", "test", "external") if (d / f"preds_{s}.csv").exists()}}
    return out


def fn_analysis(df: pd.DataFrame, thr: float) -> dict:
    fn = df[(df.y_true == 1) & (df.prob < thr)]
    pos = df[df.y_true == 1]
    return {"false_negatives": len(fn), "positives": len(pos),
            "fn_rate": len(fn) / len(pos) if len(pos) else None,
            "mean_prob_of_fn": float(fn.prob.mean()) if len(fn) else None,
            "fn_by_institution": fn.institution.value_counts().to_dict(),
            "fn_image_ids": fn.image_id.tolist()}


def evaluate_split(runs: dict, split: str, n_boot: int, seed: int) -> dict:
    res = {"models": {}, "pairwise": {}}
    names = [n for n in runs if split in runs[n]]
    for n in names:
        df, thr = runs[n][split], runs[n]["meta"]["threshold"]
        m = M.all_metrics(df.y_true, df.prob, thr)
        ci = {k: M.grouped_bootstrap_ci(df, lambda d, k=k: M.all_metrics(d.y_true, d.prob, thr)[k],
                                        n_boot=n_boot, seed=seed) for k in KEY}
        res["models"][n] = {"threshold": thr, "n_images": len(df), "n_patients": int(df.patient_id.nunique()),
                            "metrics": m, "ci95_grouped_bootstrap": ci, "fn_analysis": fn_analysis(df, thr)}
    mc, dl = [], []
    for a, b in itertools.combinations(names, 2):
        da, db = runs[a][split].set_index("image_id"), runs[b][split].set_index("image_id")
        common = da.index.intersection(db.index)
        da, db = da.loc[common], db.loc[common]
        pa = (da.prob >= runs[a]["meta"]["threshold"]).astype(int)
        pb = (db.prob >= runs[b]["meta"]["threshold"]).astype(int)
        mc.append((f"{a} vs {b}", M.mcnemar_exact(da.y_true, pa, pb)))
        dl.append((f"{a} vs {b}", M.delong_test(da.y_true, da.prob, db.prob)))
    for name, tests in (("mcnemar", mc), ("delong", dl)):
        adj = M.holm([t["p"] for _, t in tests])  # Holm within each test family
        res["pairwise"][name] = [{"pair": p, **t, "p_holm": h} for (p, t), h in zip(tests, adj)]
    return res


def to_markdown(report: dict) -> str:
    lines = [f"# Evaluation report", ""]
    if report.get("notice"):
        lines += [f"> **{report['notice']}**", ""]
    for split, r in report["splits"].items():
        lines += [f"## {split}", "", "| model | n | " + " | ".join(KEY) + " |", "|---|---|" + "---|" * len(KEY)]
        for n, m in r["models"].items():
            cells = []
            for k in KEY:
                c = m["ci95_grouped_bootstrap"][k]
                cells.append(f"{c['point']:.3f} [{c['lo']:.3f}, {c['hi']:.3f}]")
            lines.append(f"| {n} | {m['n_images']} | " + " | ".join(cells) + " |")
        for name, rows in r["pairwise"].items():
            lines += ["", f"{name} (Holm-adjusted):"]
            lines += [f"- {x['pair']}: p={x['p']:.3f}, p_holm={x['p_holm']:.3f}" for x in rows if x["p"] == x["p"]]
        lines.append("")
    lines += ["## Friedman / Wilcoxon", "", json.dumps(report["friedman_wilcoxon"]), ""]
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap =argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--n-boot", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cv-metrics", type=Path, default=None,
                    help="CSV model,block,<metric> from a grouped CV with identical blocks for all models")
    a = ap.parse_args()
    runs = load_run(a.run)
    synthetic = any(m["meta"].get("notice") for m in runs.values())
    report = {"notice": BANNER if synthetic else None, "splits": {}}
    for split in ("test", "external"):
        if any(split in r for r in runs.values()):
            report["splits"][split] = evaluate_split(runs, split, a.n_boot, a.seed)
    report["friedman_wilcoxon"] = (M.friedman_wilcoxon(pd.read_csv(a.cv_metrics)) if a.cv_metrics else
                                   {"applicable": False, "reason": "no matched CV blocks supplied (--cv-metrics); "
                                    "test-set images are not valid blocks"})
    (a.run / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (a.run / "evaluation.md").write_text(to_markdown(report), encoding="utf-8")
    print(to_markdown(report))


if __name__ == "__main__":
    main()
