"""Explainability: Elastic Net coefficients, Random Forest importances and XGBoost SHAP."""
from __future__ import annotations

import numpy as np
import pandas as pd
import shap

from .config import DAYS, DAYS_ES, LOAD_ES, LOAD_TYPES, SEED
from .features import feature_names, scenario_features

GROUPS = ("hour", "day", "load_type")
WATERFALL_CASE = {"hour": 10.0, "day": "Wednesday", "load_type": "Maximum_Load"}
DAYPARTS = {"madrugada": 3, "mañana": 10, "tarde": 15, "noche": 20}
SCENARIO_DAYS = {"Wednesday": "laborable", "Sunday": "fin de semana"}


def group_of(feature: str) -> str:
    if feature.startswith("hour_"):
        return "hour"
    return "day" if feature.startswith("day_") else "load_type"


def _base(explainer) -> float:
    return float(np.ravel(explainer.expected_value)[0])


def xgb_explainer(pipe):
    return shap.TreeExplainer(pipe.named_steps["model"])


def shap_for(pipe, features: pd.DataFrame, explainer=None) -> tuple[np.ndarray, float, np.ndarray]:
    """(shap values, base value, transformed matrix) for XGBoost on raw feature rows.

    The model only sees hour x day x load type, so at most a couple of thousand distinct rows exist: SHAP is
    computed once per distinct row and broadcast back, which is exact and much faster.
    """
    explainer = explainer or xgb_explainer(pipe)
    x = np.asarray(pipe[:-1].transform(features))
    codes = pd.factorize(pd.Series(map(tuple, np.round(x, 12))))[0]
    _, first = np.unique(codes, return_index=True)
    sv_u = np.asarray(explainer.shap_values(x[first]))
    lookup = np.zeros(codes.max() + 1, dtype=int)
    lookup[codes[first]] = np.arange(len(first))
    return sv_u[lookup[codes]], _base(explainer), x


def grouped(shap_values: np.ndarray) -> pd.DataFrame:
    """Sum SHAP values of the columns that belong to the same input (hour, day, load_type)."""
    names = feature_names()
    return pd.DataFrame({g: shap_values[:, [i for i, n in enumerate(names) if group_of(n) == g]].sum(axis=1) for g in GROUPS})


def en_coefficients(pipe) -> list[dict]:
    coef = pipe.named_steps["model"].coef_
    return [{"feature": n, "coef": float(c)} for n, c in zip(feature_names(), coef)] + [
        {"feature": "(intercepto)", "coef": float(pipe.named_steps["model"].intercept_)}
    ]


def rf_importances(pipe) -> list[dict]:
    imp = pipe.named_steps["model"].feature_importances_
    return [{"feature": n, "importance": float(v)} for n, v in zip(feature_names(), imp)]


def shap_global(shap_values: np.ndarray) -> list[dict]:
    """Mean absolute SHAP per model column."""
    return [{"feature": n, "mean_abs_shap": float(np.abs(shap_values[:, i]).mean())} for i, n in enumerate(feature_names())]


def dependence_hour(shap_values: np.ndarray, hour_frac: np.ndarray, load: np.ndarray) -> dict:
    """Mean SHAP of the hour input by fractional hour and load type (from the whole exam)."""
    g = grouped(shap_values)["hour"].to_numpy()
    df = pd.DataFrame({"h": hour_frac, "load": load, "s": g})
    hours = sorted(df["h"].unique())
    series = {}
    for lt in LOAD_TYPES:
        m = df[df["load"] == lt].groupby("h")["s"].mean().reindex(hours)
        series[lt] = [None if pd.isna(v) else float(v) for v in m]
    allm = df.groupby("h")["s"].mean().reindex(hours)
    return {"hour_frac": [float(h) for h in hours], "series": series, "all": [float(v) for v in allm]}


def waterfall_case(pipe, explainer) -> dict:
    f = scenario_features(WATERFALL_CASE["hour"], WATERFALL_CASE["day"], WATERFALL_CASE["load_type"])
    sv, base, x = shap_for(pipe, f, explainer)
    contrib = grouped(sv).iloc[0]
    names = feature_names()
    return {
        "case": dict(WATERFALL_CASE),
        "base_value": base,
        "prediction": float(base + sv[0].sum()),
        "group_contributions": {g: float(contrib[g]) for g in GROUPS},
        "features": [{"feature": n, "value": float(x[0, i]), "shap": float(sv[0, i])} for i, n in enumerate(names)],
    }


def daypart_of(hour: int) -> str:
    if hour < 6:
        return "madrugada"
    if hour < 12:
        return "mañana"
    return "tarde" if hour < 18 else "noche"


def scenario_phrase(hour: int, day: str, load_type: str, base: float, contrib: dict, xgb_kwh: float,
                    exported_model: str, exported_kwh: float) -> str:
    """Short Spanish sentence from the SHAP contributions of one scenario."""
    load = LOAD_ES[load_type].lower()
    parts = sorted(contrib.items(), key=lambda kv: -abs(kv[1]))
    label = {"hour": f"la hora ({daypart_of(hour)})", "day": f"el día ({DAYS_ES[day].lower()})", "load_type": f"la {load}"}
    detail = ", ".join(f"{label[k]} {v:+.1f} kWh" for k, v in parts)
    text = (
        f"{load.capitalize()}, {DAYS_ES[day].lower()} a las {hour:02d}:00: {detail} frente al promedio de la planta "
        f"({base:.1f} kWh); XGBoost estima {xgb_kwh:.1f} kWh."
    )
    if exported_model != "XGBoost":
        text += f" El modelo exportado ({exported_model}) estima {exported_kwh:.1f} kWh."
    return text


def scenario_explanations(xgb_pipe, explainer, table_lookup, exported_model: str) -> list[dict]:
    """Typical scenarios (four dayparts x weekday/weekend x three load types) explained with XGBoost SHAP."""
    out = []
    for part, hour in DAYPARTS.items():
        for day in SCENARIO_DAYS:
            for lt in LOAD_TYPES:
                f = scenario_features(hour + np.array([0, 0.25, 0.5, 0.75]), day, lt)
                sv, base, _ = shap_for(xgb_pipe, f, explainer)
                contrib = grouped(sv).mean()
                xgb_kwh = float(base + sv.sum(axis=1).mean())
                kwh = table_lookup(hour, day, lt)
                out.append({
                    "id": f"{part}_{day}_{lt}", "hour": hour, "day": day, "load_type": lt, "kwh": kwh,
                    "phrase": scenario_phrase(hour, day, lt, base, {g: float(contrib[g]) for g in GROUPS}, xgb_kwh,
                                              exported_model, kwh),
                })
    return out


def summary_sample(pipe, features: pd.DataFrame, meta: pd.DataFrame, explainer, n: int = 1500) -> pd.DataFrame:
    """Random sample of the exam with SHAP values per column (for the beeswarm summary)."""
    idx = features.sample(n=min(n, len(features)), random_state=SEED).sort_index().index
    sv, base, x = shap_for(pipe, features.loc[idx], explainer)
    names = feature_names()
    out = pd.DataFrame(x, columns=names, index=idx)
    for i, nme in enumerate(names):
        out[f"shap_{nme}"] = sv[:, i]
    out["base_value"] = base
    out["hour_frac"] = meta.loc[idx, "hour_frac"].to_numpy()
    return out.reset_index(drop=True)
