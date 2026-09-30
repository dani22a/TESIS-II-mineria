"""Build, validate and query the JSON artifact the twin reads (artefactos/planta_xgboost.json)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DAYS, FINAL_ARTIFACT, LOAD_TYPES, MODELS, SEED, TARGET, UNIT
from .contract import variable_contract
from .features import scenario_features

SCHEMA_VERSION = 1
TOP_LEVEL_KEYS = [
    "schema_version", "target", "unit", "model", "seed", "variable_contract", "hyperparameters",
    "exam_metrics", "prediction_table", "scenario_explanations", "stats_summary", "notes",
]


def prediction_table(pipe) -> list[dict]:
    """24 hours x 7 days x 3 load types = 504 rows; kWh of an hour = mean of the :00/:15/:30/:45 predictions."""
    rows = []
    for load in LOAD_TYPES:
        for day in DAYS:
            for hour in range(24):
                rows.append((hour, day, load))
    frames = [scenario_features(h + np.array([0, 0.25, 0.5, 0.75]), d, lt).assign(key=i) for i, (h, d, lt) in enumerate(rows)]
    big = pd.concat(frames, ignore_index=True)
    big["pred"] = pipe.predict(big.drop(columns="key"))
    mean = big.groupby("key")["pred"].mean().to_numpy()
    return [{"hour": h, "day": d, "load_type": lt, "kwh": round(float(k), 2)} for (h, d, lt), k in zip(rows, mean)]


def co2_factor(df: pd.DataFrame) -> float:
    """tCO2 per kWh, derived from the data (sum of CO2 over sum of kWh)."""
    return float(df["CO2(tCO2)"].sum() / df[TARGET].sum())


def build_artifact(*, exported_model: str, hyperparameters: dict, exam_metrics: dict, table: list[dict],
                   scenarios: list[dict], stats_summary: dict, co2_tco2_per_kwh: float, split: dict) -> dict:
    contract = variable_contract()
    contract["post_computed"] = {
        "co2_tco2": {
            "formula": "co2_tco2 = kwh * factor",
            "factor_tco2_per_kwh": co2_tco2_per_kwh,
            "note": "CO2 is derived from kWh after the prediction; it never enters the model.",
        }
    }
    contract["load_type_rule_summary"] = "load_type from SAG tonnage / nominal: < 0.75 Light, <= 0.90 Medium, > 0.90 Maximum"
    notes = [
        f"El modelo exportado es {exported_model}: el de menor MAE en el examen (1 oct a 31 dic 2018), entrenado solo con 1 ene a 30 sep.",
        "La tabla de predicción promedia las predicciones de los minutos :00, :15, :30 y :45 de cada hora; el valor es kWh por intervalo de 15 min.",
        "Las frases de scenario_explanations provienen de los valores SHAP de XGBoost (aporte de hora, día y carga sobre el promedio de la planta).",
        "Combinaciones que casi no ocurren en los datos (por ejemplo carga máxima en domingo de madrugada) son extrapolaciones del modelo.",
        "El CO2 no entra al modelo: se calcula como kWh por el factor de variable_contract.post_computed.",
        f"Corte por inicio de intervalo: entrenamiento hasta {split['train_end'][:16]}, examen desde {split['exam_start'][:16]}.",
        "MAPE se calcula solo sobre registros con consumo real mayor o igual a 1 kWh.",
    ]
    if exported_model != "XGBoost":
        notes.append(
            f"El ganador no es XGBoost: prediction_table y kwh provienen de {exported_model}; las frases SHAP siguen siendo de XGBoost, "
            "como indica el plan."
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "target": TARGET,
        "unit": UNIT,
        "model": exported_model,
        "seed": SEED,
        "variable_contract": contract,
        "hyperparameters": hyperparameters,
        "exam_metrics": exam_metrics,
        "prediction_table": table,
        "scenario_explanations": scenarios,
        "stats_summary": stats_summary,
        "notes": notes,
    }


def _finite(obj) -> bool:
    if isinstance(obj, float):
        return math.isfinite(obj)
    if isinstance(obj, dict):
        return all(_finite(v) for v in obj.values())
    if isinstance(obj, list):
        return all(_finite(v) for v in obj)
    return True


def validate_artifact(a: dict) -> list[str]:
    """Return a list of problems (empty when the artifact matches the agreed schema)."""
    errors = []
    if set(a.keys()) != set(TOP_LEVEL_KEYS):
        errors.append(f"top-level keys differ: {sorted(set(a) ^ set(TOP_LEVEL_KEYS))}")
    if a.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if a.get("target") != TARGET or a.get("unit") != UNIT or a.get("seed") != SEED:
        errors.append("target/unit/seed mismatch")
    if a.get("model") not in MODELS:
        errors.append("model must be one of the three models")
    table = a.get("prediction_table", [])
    if len(table) != 24 * 7 * 3:
        errors.append(f"prediction_table has {len(table)} rows, expected 504")
    seen = set()
    for r in table:
        if set(r) != {"hour", "day", "load_type", "kwh"}:
            errors.append("prediction_table row with wrong keys")
            break
        if r["day"] not in DAYS or r["load_type"] not in LOAD_TYPES or r["hour"] not in range(24):
            errors.append(f"prediction_table invalid row {r}")
            break
        seen.add((r["hour"], r["day"], r["load_type"]))
    if len(seen) != 504:
        errors.append("prediction_table does not cover every hour x day x load type once")
    if not _finite(a):
        errors.append("non-finite number found")
    sc = a.get("scenario_explanations", [])
    if len(sc) < 12:
        errors.append(f"scenario_explanations has {len(sc)} items, expected at least 12")
    for s in sc:
        if set(s) != {"id", "hour", "day", "load_type", "kwh", "phrase"} or not s.get("phrase"):
            errors.append(f"scenario {s.get('id')} malformed")
            break
    em = a.get("exam_metrics", {})
    per = em.get("per_model", {})
    if set(per) != set(MODELS) or em.get("exported") != a.get("model"):
        errors.append("exam_metrics must cover the three models and name the exported one")
    for m, v in per.items():
        if not {"mae", "rmse", "mape", "r2"} <= set(v):
            errors.append(f"exam_metrics for {m} incomplete")
    if set(a.get("hyperparameters", {})) != set(MODELS):
        errors.append("hyperparameters must cover the three models")
    if not isinstance(a.get("notes"), list) or not a["notes"]:
        errors.append("notes must be a non-empty list")
    return errors


def load_artifact(path: Path = FINAL_ARTIFACT) -> dict | None:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def lookup_kwh(a: dict, hour: int, day: str, load_type: str) -> float:
    """kWh per 15 min for an (hour, day, load type) scenario from the exported table."""
    for r in a["prediction_table"]:
        if r["hour"] == hour and r["day"] == day and r["load_type"] == load_type:
            return r["kwh"]
    raise KeyError((hour, day, load_type))


def lookup_explanation(a: dict, hour: int, day: str, load_type: str) -> tuple[dict | None, bool]:
    """Best typical-scenario explanation: exact match, else nearest hour with the same load type and day kind.

    Returns (scenario or None, exact).
    """
    scenarios = a["scenario_explanations"]
    for s in scenarios:
        if (s["hour"], s["day"], s["load_type"]) == (hour, day, load_type):
            return s, True
    weekend = day in ("Saturday", "Sunday")
    pool = [s for s in scenarios if s["load_type"] == load_type and (s["day"] in ("Saturday", "Sunday")) == weekend]
    if not pool:
        return None, False
    return min(pool, key=lambda s: abs(s["hour"] - hour)), False


def co2_from_kwh(a: dict, kwh: float) -> float:
    """tCO2 for a kWh amount using the factor stored in the artifact (post-computed, not modelled)."""
    return kwh * a["variable_contract"]["post_computed"]["co2_tco2"]["factor_tco2_per_kwh"]
