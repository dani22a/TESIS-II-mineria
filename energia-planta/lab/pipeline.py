"""Orchestration shared by train.py and the Streamlit buttons. Results are cached under artefactos/."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import data as data_mod
from . import modeling
from .config import ARTIFACTS, DATA_PATH, MODELS, SEED, TARGET
from .features import make_features

FROZEN = "hiperparametros_congelados.json"
SEARCH = "busqueda_cv.json"


def write_json(name: str, obj, directory: Path = ARTIFACTS) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_json(name: str, directory: Path = ARTIFACTS):
    path = directory / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_prepared(path: Path = DATA_PATH) -> pd.DataFrame:
    return data_mod.prepare(data_mod.load_raw(path))


def split_frames(df: pd.DataFrame):
    """(train_df, exam_df) by interval start; exam = Oct 1 onwards."""
    tr, ex = data_mod.split_masks(df)
    return df[tr].copy(), df[ex].copy()


def split_summary(df: pd.DataFrame) -> dict:
    train, exam = split_frames(df)
    return {
        "train_start": str(train["ts_start"].min()), "train_end": str(train["ts_start"].max()),
        "exam_start": str(exam["ts_start"].min()), "exam_end": str(exam["ts_start"].max()),
        "n_train": int(len(train)), "n_exam": int(len(exam)),
        "note": "Split by interval start (ts_start). The 2019-01-01 00:00 record starts at 2018-12-31 23:45 and belongs to the exam.",
    }


def run_modeling(progress=None, n_iter: dict | None = None, directory: Path = ARTIFACTS) -> dict:
    """Phase 6: temporal hyperparameter search on Jan-Sep only, then freeze the winners to JSON."""
    if progress:
        progress("Cargando datos", 0.0)
    df = load_prepared()
    train, _ = split_frames(df)
    X, y = make_features(train), train[TARGET]

    def _progress(msg, frac):
        if progress:
            progress(msg, frac)

    results = modeling.run_search(X, y, MODELS, n_iter=n_iter, progress=_progress)
    frozen = {
        "seed": SEED,
        "scoring": modeling.SCORING,
        "split": split_summary(df),
        "cv": {"type": "TimeSeriesSplit", "n_splits": modeling.N_SPLITS,
               "folds": modeling.cv_folds(train["ts_start"])},
        "models": {n: {k: v for k, v in r.items() if k != "top_candidates"} for n, r in results.items()},
    }
    write_json(FROZEN, frozen, directory)
    write_json(SEARCH, {n: r["top_candidates"] for n, r in results.items()}, directory)
    return frozen
