"""Exam evaluation: metrics, weekly windows, Friedman + Nemenyi and Diebold-Mariano."""
from __future__ import annotations

import numpy as np
import pandas as pd
import scikit_posthocs as sp
import statsmodels.api as sm
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .config import EXAM_START, MODELS, TARGET

MAPE_MIN_KWH = 1.0  # MAPE is undefined near zero: rows with y < 1 kWh are excluded from it.
WINDOW_DAYS = 7
SLOTS_PER_WINDOW = WINDOW_DAYS * 96


def compute_metrics(y_true, y_pred) -> dict:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    mask = y_true >= MAPE_MIN_KWH
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape": float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100),
        "r2": float(r2_score(y_true, y_pred)),
        "n_mape": int(mask.sum()),
        "n": int(len(y_true)),
    }


def weekly_windows(exam: pd.DataFrame, preds: dict[str, np.ndarray]) -> pd.DataFrame:
    """MAE per complete 7-day window of the exam period, one column per model."""
    frame = pd.DataFrame({"window": ((exam["ts_start"] - EXAM_START) // pd.Timedelta(days=WINDOW_DAYS)).to_numpy(),
                          "ts_start": exam["ts_start"].to_numpy(), "y": exam[TARGET].to_numpy()})
    for m in MODELS:
        frame[m] = np.abs(frame["y"] - np.asarray(preds[m]))
    g = frame.groupby("window")
    out = g[MODELS].mean()
    out["n"] = g.size()
    out["start"] = g["ts_start"].min().dt.strftime("%Y-%m-%d")
    out["end"] = g["ts_start"].max().dt.strftime("%Y-%m-%d")
    out = out[out["n"] == SLOTS_PER_WINDOW].reset_index()
    return out


def friedman_nemenyi(windows: pd.DataFrame) -> dict:
    """Friedman test over the windows (blocks) and Nemenyi post hoc on the mean ranks."""
    mat = windows[MODELS].to_numpy()
    chi2, p = stats.friedmanchisquare(*[mat[:, i] for i in range(mat.shape[1])])
    ranks = pd.DataFrame(mat, columns=MODELS).rank(axis=1)
    nem = sp.posthoc_nemenyi_friedman(mat)
    nem.index = nem.columns = MODELS
    return {
        "n_windows": int(mat.shape[0]),
        "chi2": float(chi2),
        "p": float(p),
        "mean_ranks": {m: float(ranks[m].mean()) for m in MODELS},
        "nemenyi": {a: {b: float(nem.loc[a, b]) for b in MODELS} for a in MODELS},
    }


def diebold_mariano(err_a, err_b, lags: int | None = None) -> dict:
    """Diebold-Mariano with absolute-error loss and a Newey-West (HAC) variance, one-step horizon.

    The loss differential d = |e_a| - |e_b| is regressed on a constant with HAC standard errors. A negative
    statistic means model A has the lower loss. ``lags`` defaults to the Newey-West rule 4*(T/100)^(2/9).
    """
    d = np.abs(np.asarray(err_a, float)) - np.abs(np.asarray(err_b, float))
    t = len(d)
    lags = int(lags if lags is not None else np.floor(4 * (t / 100) ** (2 / 9)))
    fit = sm.OLS(d, np.ones(t)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"stat": float(fit.tvalues[0]), "p": float(fit.pvalues[0]), "mean_diff": float(d.mean()), "lags": lags, "n": t}


def dm_last_month(exam: pd.DataFrame, preds: dict[str, np.ndarray], base: str = "XGBoost") -> list[dict]:
    """DM on December: `base` against each rival, with the NW rule lag and a one-day lag (96) for sensitivity."""
    last = exam["ts_start"].dt.month == 12
    err = {m: (exam[TARGET].to_numpy() - np.asarray(preds[m]))[last.to_numpy()] for m in MODELS}
    rows = []
    for rival in MODELS:
        if rival == base:
            continue
        main = diebold_mariano(err[base], err[rival])
        day_lag = diebold_mariano(err[base], err[rival], lags=96)
        rows.append({
            "model_a": base, "model_b": rival, "n": main["n"], "mae_a": float(np.mean(np.abs(err[base]))),
            "mae_b": float(np.mean(np.abs(err[rival]))), "mean_diff": main["mean_diff"],
            "stat": main["stat"], "p": main["p"], "lags": main["lags"],
            "stat_lag96": day_lag["stat"], "p_lag96": day_lag["p"],
        })
    return rows
