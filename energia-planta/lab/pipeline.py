"""Orchestration shared by train.py and the Streamlit buttons. Results are cached under artefactos/."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from . import data as data_mod
from . import evaluation, explain, export, modeling, stats_tests
from .config import ARTIFACTS, DATA_PATH, MODELS, SEED, TARGET
from .features import make_features

FROZEN = "hiperparametros_congelados.json"
SEARCH = "busqueda_cv.json"
METRICS = "metricas_examen.json"
WINDOWS = "ventanas_mae.json"
MODEL_TESTS = "pruebas_modelos.json"
EXPLAIN = "explicabilidad.json"
PREDICTIONS = "predicciones_examen.csv"
SHAP_SAMPLE = "shap_muestra.csv"
MODELS_FILE = "modelos.joblib"
FINAL = "planta_xgboost.json"


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


def _stats_summary(t: dict, fn: dict, dm: list[dict]) -> dict:
    """Brief, JSON-friendly outcome of the key tests."""
    kl, mw, sp_ = t["kruskal_load"], t["mann_whitney"], t["spearman"].set_index("variable")["rho"]
    vif = t["vif"].set_index("variable")["VIF con CO2"]
    k = t["kpss"].iloc[0]
    return {
        "kruskal_wallis_load_type": {"H": kl["H"], "p": kl["p"], "epsilon2": kl["eps2"],
                                     "dunn_all_pairs_p_lt_0.001": bool(((kl["dunn"].to_numpy() < 0.001) | (kl["dunn"].to_numpy() == 1.0)).all())},
        "mann_whitney_weekday_vs_weekend": {"U": mw["U"], "p": mw["p"], "median_weekday": mw["median_weekday"],
                                            "median_weekend": mw["median_weekend"]},
        "spearman_with_kwh": {c: float(sp_[c]) for c in stats_tests.NUMERIC},
        "vif_with_co2": {"CO2(tCO2)": float(vif["CO2(tCO2)"]), "Usage_kWh": float(vif["Usage_kWh"])},
        "kpss_level": {"statistic": float(k["estadístico"]), "p_bounded": float(k["p (acotado a 0.01-0.10)"])},
        "friedman_weekly_mae": {"n_windows": fn["n_windows"], "chi2": fn["chi2"], "p": fn["p"], "mean_ranks": fn["mean_ranks"]},
        "nemenyi_p": fn["nemenyi"],
        "diebold_mariano_december_abs_error": [
            {"a": r["model_a"], "b": r["model_b"], "stat": r["stat"], "p_nw": r["p"], "p_lag96": r["p_lag96"], "mean_loss_diff_kwh": r["mean_diff"]}
            for r in dm
        ],
    }


def run_all(progress=None, reuse_search: bool = False, n_iter: dict | None = None,
            directory: Path = ARTIFACTS, final_path: Path | None = None) -> dict:
    """Phases 5-8 end to end: search -> freeze -> exam -> stats -> SHAP -> export. Returns the final artifact."""
    def step(msg, frac):
        if progress:
            progress(msg, frac)

    step("Cargando datos", 0.0)
    df = load_prepared()
    train, exam = split_frames(df)
    X_tr, y_tr, X_ex, y_ex = make_features(train), train[TARGET], make_features(exam), exam[TARGET]

    frozen = read_json(FROZEN, directory) if reuse_search else None
    if frozen is None:
        frozen = run_modeling(progress=lambda m, f: step(m, 0.05 + 0.45 * f), n_iter=n_iter, directory=directory)
    params = {m: frozen["models"][m]["params"] for m in MODELS}

    step("Entrenando con hiperparámetros congelados (1 ene a 30 sep)", 0.52)
    fitted = {m: modeling.build_pipeline(m, params[m]).fit(X_tr, y_tr) for m in MODELS}
    joblib.dump(fitted, directory / MODELS_FILE)

    step("Evaluando en el examen (1 oct a 31 dic)", 0.6)
    preds = {m: fitted[m].predict(X_ex) for m in MODELS}
    metrics = {m: evaluation.compute_metrics(y_ex, preds[m]) for m in MODELS}
    exported = min(MODELS, key=lambda m: metrics[m]["mae"])
    write_json(METRICS, {"per_model": metrics, "exported": exported, "criterion": "lowest MAE on the exam",
                         "mape_rule": f"MAPE only on rows with actual kWh >= {evaluation.MAPE_MIN_KWH}"}, directory)
    pred_frame = pd.DataFrame({"ts_start": exam["ts_start"].to_numpy(), "hour_frac": exam["hour_frac"].to_numpy(),
                               "day": exam["day"].to_numpy(), "load_type": exam["Load_Type"].to_numpy(),
                               "y": y_ex.to_numpy(), **{m: preds[m] for m in MODELS}})
    pred_frame.to_csv(directory / PREDICTIONS, index=False)

    step("Pruebas entre modelos (Friedman, Nemenyi, Diebold-Mariano)", 0.68)
    windows = evaluation.weekly_windows(exam, preds)
    fn = evaluation.friedman_nemenyi(windows)
    dm = evaluation.dm_last_month(exam, preds, base="XGBoost")
    write_json(WINDOWS, windows.to_dict(orient="records"), directory)
    write_json(MODEL_TESTS, {"friedman_nemenyi": fn, "diebold_mariano": dm,
                             "dm_note": "Absolute-error loss on December; HAC (Newey-West) variance; p_lag96 uses a one-day bandwidth."}, directory)

    step("Explicabilidad: coeficientes, importancias y SHAP", 0.78)
    xgb = fitted["XGBoost"]
    explainer = explain.xgb_explainer(xgb)
    sv, base, _ = explain.shap_for(xgb, X_ex, explainer)
    sample = explain.summary_sample(xgb, X_ex, exam, explainer)
    sample.to_csv(directory / SHAP_SAMPLE, index=False)
    write_json(EXPLAIN, {
        "elastic_net_coefficients": explain.en_coefficients(fitted["Elastic Net"]),
        "random_forest_importances": explain.rf_importances(fitted["Random Forest"]),
        "xgboost_shap_global": explain.shap_global(sv),
        "xgboost_shap_base_value": base,
        "dependence_hour": explain.dependence_hour(sv, exam["hour_frac"].to_numpy(), exam["Load_Type"].to_numpy()),
        "waterfall": explain.waterfall_case(xgb, explainer),
    }, directory)

    step("Pruebas estadísticas de los datos y exportación", 0.9)
    tests = stats_tests.run_data_tests(df)
    table = export.prediction_table(fitted[exported])
    lookup = {(r["hour"], r["day"], r["load_type"]): r["kwh"] for r in table}
    scenarios = explain.scenario_explanations(xgb, explainer, lambda h, d, lt: lookup[(h, d, lt)], exported)
    artifact = export.build_artifact(
        exported_model=exported,
        hyperparameters={m: params[m] for m in MODELS},
        exam_metrics={"per_model": {m: {k: v for k, v in metrics[m].items() if k in ("mae", "rmse", "mape", "r2")} for m in MODELS},
                      "exported": exported, "unit": "kWh (MAPE in %)", "criterion": "lowest exam MAE"},
        table=table, scenarios=scenarios, stats_summary=_stats_summary(tests, fn, dm),
        co2_tco2_per_kwh=export.co2_factor(df), split=frozen["split"],
    )
    problems = export.validate_artifact(artifact)
    if problems:
        raise ValueError("Artifact failed validation: " + "; ".join(problems))
    final_dir = final_path.parent if final_path else directory
    write_json(final_path.name if final_path else FINAL, artifact, final_dir)
    step("Listo", 1.0)
    return artifact
