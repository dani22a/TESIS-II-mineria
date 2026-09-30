"""Model pipelines, search spaces and the temporal hyperparameter search (train period only)."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint, uniform
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from .config import MODELS, SEED
from .features import build_preprocessor

N_SPLITS = 5
SCORING = "neg_mean_absolute_error"
DEFAULT_N_ITER = {"Elastic Net": 30, "Random Forest": 15, "XGBoost": 30}


def build_pipeline(name: str, params: dict | None = None) -> Pipeline:
    """Create the pipeline of a model. Elastic Net scales inside; trees do not."""
    params = params or {}
    if name == "Elastic Net":
        pipe = Pipeline([
            ("prep", build_preprocessor()),
            ("scale", StandardScaler()),
            ("model", ElasticNet(max_iter=20000, random_state=SEED)),
        ])
    elif name == "Random Forest":
        pipe = Pipeline([
            ("prep", build_preprocessor()),
            ("model", RandomForestRegressor(random_state=SEED, n_jobs=1)),
        ])
    elif name == "XGBoost":
        pipe = Pipeline([
            ("prep", build_preprocessor()),
            ("model", XGBRegressor(random_state=SEED, n_jobs=1, tree_method="hist", verbosity=0)),
        ])
    else:
        raise ValueError(f"Unknown model: {name}")
    if params:
        pipe.set_params(**{f"model__{k}": v for k, v in params.items()})
    return pipe


# Search spaces: (scipy distribution, Spanish description for the screen).
SEARCH_SPACES = {
    "Elastic Net": {
        "alpha": (loguniform(1e-3, 10), "log-uniforme entre 0.001 y 10"),
        "l1_ratio": (uniform(0.05, 0.90), "uniforme entre 0.05 y 0.95"),
    },
    "Random Forest": {
        "n_estimators": (randint(100, 401), "entero entre 100 y 400"),
        "max_depth": (randint(3, 21), "entero entre 3 y 20"),
        "min_samples_leaf": (randint(1, 41), "entero entre 1 y 40"),
    },
    "XGBoost": {
        "n_estimators": (randint(100, 601), "entero entre 100 y 600"),
        "max_depth": (randint(2, 9), "entero entre 2 y 8"),
        "learning_rate": (loguniform(0.01, 0.3), "log-uniforme entre 0.01 y 0.3"),
        "subsample": (uniform(0.6, 0.4), "uniforme entre 0.6 y 1.0"),
        "colsample_bytree": (uniform(0.6, 0.4), "uniforme entre 0.6 y 1.0"),
        "reg_lambda": (loguniform(0.1, 20), "log-uniforme entre 0.1 y 20"),
    },
}


def _py(v):
    """Numpy scalar -> plain Python value (JSON friendly)."""
    if isinstance(v, np.generic):
        return v.item()
    return v


def cv_folds(train_index: pd.DatetimeIndex | pd.Series, n_splits: int = N_SPLITS) -> list[dict]:
    """Describe the TimeSeriesSplit folds over the (time-sorted) train timestamps."""
    ts = pd.Series(pd.to_datetime(train_index)).reset_index(drop=True)
    out = []
    for i, (tr, va) in enumerate(TimeSeriesSplit(n_splits=n_splits).split(ts), start=1):
        out.append({
            "fold": i,
            "train_start": str(ts.iloc[tr[0]]), "train_end": str(ts.iloc[tr[-1]]),
            "val_start": str(ts.iloc[va[0]]), "val_end": str(ts.iloc[va[-1]]),
            "n_train": int(len(tr)), "n_val": int(len(va)),
        })
    return out


def search_model(name: str, X: pd.DataFrame, y: pd.Series, n_iter: int | None = None) -> dict:
    """RandomizedSearchCV over a TimeSeriesSplit; returns frozen params and a CV summary."""
    n_iter = n_iter or DEFAULT_N_ITER[name]
    dists = {f"model__{k}": v[0] for k, v in SEARCH_SPACES[name].items()}
    search = RandomizedSearchCV(
        build_pipeline(name), dists, n_iter=n_iter, cv=TimeSeriesSplit(n_splits=N_SPLITS),
        scoring=SCORING, random_state=SEED, n_jobs=-1, refit=False, return_train_score=False,
    )
    t0 = time.time()
    search.fit(X, y)
    seconds = time.time() - t0

    res = pd.DataFrame(search.cv_results_)
    fold_cols = [f"split{i}_test_score" for i in range(N_SPLITS)]
    res["cv_mae"] = -res["mean_test_score"]
    res["cv_mae_std"] = res["std_test_score"]
    best = int(res["cv_mae"].idxmin())
    params = {k.removeprefix("model__"): _py(v) for k, v in search.cv_results_["params"][best].items()}
    top = res.sort_values("cv_mae").head(10)
    return {
        "params": params,
        "cv_mae": float(res.loc[best, "cv_mae"]),
        "cv_mae_std": float(res.loc[best, "cv_mae_std"]),
        "cv_mae_folds": [float(-res.loc[best, c]) for c in fold_cols],
        "n_iter": int(n_iter),
        "seconds": round(seconds, 1),
        "search_space": {k: v[1] for k, v in SEARCH_SPACES[name].items()},
        "top_candidates": [
            {"rank": r + 1, "cv_mae": float(row["cv_mae"]), "cv_mae_std": float(row["cv_mae_std"]),
             **{k.removeprefix("model__"): _py(v) for k, v in row["params"].items()}}
            for r, (_, row) in enumerate(top.iterrows())
        ],
    }


def run_search(X: pd.DataFrame, y: pd.Series, models=MODELS, n_iter: dict | None = None, progress=None) -> dict:
    """Search every model on the train period and return the results per model."""
    results = {}
    for i, name in enumerate(models):
        if progress:
            progress(f"Buscando hiperparámetros: {name}", i / len(models))
        results[name] = search_model(name, X, y, (n_iter or {}).get(name))
    if progress:
        progress("Búsqueda terminada", 1.0)
    return results
