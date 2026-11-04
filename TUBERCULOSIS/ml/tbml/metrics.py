"""Metrics and statistical tests. Pure numpy/scipy/sklearn (no torch)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (average_precision_score, f1_score, matthews_corrcoef, roc_auc_score)


def confusion(y, pred) -> dict:
    y, pred = np.asarray(y).astype(int), np.asarray(pred).astype(int)
    tp = int(((y == 1) & (pred == 1)).sum()); tn = int(((y == 0) & (pred == 0)).sum())
    fp = int(((y == 0) & (pred == 1)).sum()); fn = int(((y == 1) & (pred == 0)).sum())
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn}


def _safe(fn, *a):
    try:
        return float(fn(*a))
    except ValueError:  # single-class sample
        return float("nan")


def expected_calibration_error(y, prob, bins: int = 10) -> float:
    y, prob = np.asarray(y, float), np.asarray(prob, float)
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(prob, edges[1:-1]), 0, bins - 1)
    ece = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            ece += m.mean() * abs(y[m].mean() - prob[m].mean())
    return float(ece)


def all_metrics(y, prob, threshold: float) -> dict:
    y, prob = np.asarray(y).astype(int), np.asarray(prob, float)
    pred = (prob >= threshold).astype(int)
    c = confusion(y, pred)
    sens = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else float("nan")
    spec = c["tn"] / (c["tn"] + c["fp"]) if (c["tn"] + c["fp"]) else float("nan")
    return {**c, "sensitivity": sens, "specificity": spec, "f1": _safe(f1_score, y, pred),
            "mcc": _safe(matthews_corrcoef, y, pred), "auc_roc": _safe(roc_auc_score, y, prob),
            "auc_pr": _safe(average_precision_score, y, prob),
            "brier": float(np.mean((prob - y) ** 2)), "ece": expected_calibration_error(y, prob)}


def grouped_bootstrap_ci(df: pd.DataFrame, metric_fn, group_col: str = "patient_id", n_boot: int = 1000,
                         seed: int = 0, alpha: float = 0.05) -> dict:
    """Percentile CI resampling whole groups (patients) so repeated images of a patient stay together.
    metric_fn(df) -> float. Resamples with a single class are skipped (and counted)."""
    rng = np.random.default_rng(seed)
    groups = {g: np.asarray(ix) for g, ix in df.groupby(group_col).indices.items()}
    keys = list(groups)
    vals, skipped = [], 0
    for _ in range(n_boot):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        sample = df.iloc[np.concatenate([groups[keys[i]] for i in pick])]
        v = metric_fn(sample)
        if np.isnan(v):
            skipped += 1
        else:
            vals.append(v)
    point = metric_fn(df)
    if len(vals) < 10:
        return {"point": point, "lo": float("nan"), "hi": float("nan"), "n_boot": len(vals), "skipped": skipped}
    lo, hi = np.quantile(vals, [alpha / 2, 1 - alpha / 2])
    return {"point": point, "lo": float(lo), "hi": float(hi), "n_boot": len(vals), "skipped": skipped}


def mcnemar_exact(y, pred_a, pred_b) -> dict:
    """Exact McNemar on discordant pairs. NOTE: treats images as independent; collapse to one
    image per patient when patients contribute several images."""
    y, a, b = (np.asarray(v).astype(int) for v in (y, pred_a, pred_b))
    ca, cb = a == y, b == y
    n01 = int((ca & ~cb).sum())  # A right, B wrong
    n10 = int((~ca & cb).sum())
    n = n01 + n10
    p = 1.0 if n == 0 else float(stats.binomtest(min(n01, n10), n, 0.5).pvalue)
    return {"a_only_correct": n01, "b_only_correct": n10, "p": p}


def _midrank(x):
    order = np.argsort(x)
    z = x[order]
    n = len(x)
    t = np.zeros(n)
    i = 0
    while i < n:
        j = i
        while j < n and z[j] == z[i]:
            j += 1
        t[i:j] = 0.5 * (i + j - 1) + 1
        i = j
    out = np.empty(n)
    out[order] = t
    return out


def delong_test(y, score_a, score_b) -> dict:
    """Paired DeLong test for the difference of two correlated AUCs (Sun & Xu 2014 fast version)."""
    y = np.asarray(y).astype(int)
    order = np.argsort(-y, kind="stable")  # positives first
    m = int(y.sum())
    n = len(y) - m
    if m == 0 or n == 0:
        return {"auc_a": float("nan"), "auc_b": float("nan"), "z": float("nan"), "p": float("nan")}
    preds = np.vstack([np.asarray(score_a, float)[order], np.asarray(score_b, float)[order]])
    pos, neg = preds[:, :m], preds[:, m:]
    tx = np.array([_midrank(p) for p in pos]); ty = np.array([_midrank(p) for p in neg])
    tz = np.array([_midrank(p) for p in preds])
    aucs = tz[:, :m].sum(axis=1) / m / n - (m + 1.0) / 2.0 / n
    v01 = (tz[:, :m] - tx) / n
    v10 = 1.0 - (tz[:, m:] - ty) / m
    s = np.cov(v01) / m + np.cov(v10) / n
    var = s[0, 0] + s[1, 1] - 2 * s[0, 1]
    if var <= 0:
        return {"auc_a": float(aucs[0]), "auc_b": float(aucs[1]), "z": float("nan"), "p": float("nan")}
    z = (aucs[0] - aucs[1]) / np.sqrt(var)
    return {"auc_a": float(aucs[0]), "auc_b": float(aucs[1]), "z": float(z), "p": float(2 * stats.norm.sf(abs(z)))}


def holm(pvalues: list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values (NaN kept as NaN)."""
    p = np.asarray(pvalues, float)
    ok = ~np.isnan(p)
    out = np.full_like(p, np.nan)
    idx = np.argsort(p[ok])
    m = ok.sum()
    adj = np.maximum.accumulate((m - np.arange(m)) * p[ok][idx])
    res = np.empty(m)
    res[idx] = np.minimum(adj, 1.0)
    out[ok] = res
    return out.tolist()


def friedman_wilcoxon(cv: pd.DataFrame, metric: str = "auc_roc", min_blocks: int = 5) -> dict:
    """Friedman + pairwise Wilcoxon (Holm) over matched blocks.

    cv columns: model, block, <metric>. A 'block' is one resampling unit shared by ALL models (e.g. the
    same grouped CV fold). Refuses (returns applicable=False) unless >=3 models share >=min_blocks
    identical blocks; test-set images are NOT blocks.
    """
    wide = cv.pivot_table(index="block", columns="model", values=metric).dropna()
    if wide.shape[1] < 3 or wide.shape[0] < min_blocks:
        return {"applicable": False, "reason": f"need >=3 models and >={min_blocks} shared blocks; "
                                               f"got {wide.shape[1]} models, {wide.shape[0]} blocks"}
    fr = stats.friedmanchisquare(*[wide[c] for c in wide.columns])
    pairs, ps = [], []
    cols = list(wide.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            d = wide[cols[i]] - wide[cols[j]]
            p = 1.0 if (d == 0).all() else float(stats.wilcoxon(wide[cols[i]], wide[cols[j]]).pvalue)
            pairs.append(f"{cols[i]} vs {cols[j]}"); ps.append(p)
    return {"applicable": True, "friedman_chi2": float(fr.statistic), "friedman_p": float(fr.pvalue),
            "blocks": int(wide.shape[0]),
            "wilcoxon": [{"pair": a, "p": p, "p_holm": h} for a, p, h in zip(pairs, ps, holm(ps))]}
