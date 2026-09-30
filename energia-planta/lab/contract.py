"""Variable contract: single source of truth shared by the Negocio screen and the JSON export."""
from __future__ import annotations

from .config import DAYS, LOAD_THRESHOLDS, LOAD_TYPES, SEED, TARGET, UNIT
from .features import feature_names

# Model inputs: only what the digital twin can produce.
INPUTS = [
    {
        "name": "hour",
        "type": "float (hour of day at interval start)",
        "allowed": "0 to 23.75 in steps of 0.25 (the exported table uses integer hours 0-23)",
        "twin_signal": "Simulation clock of the twin (hour + minute/60)",
        "model_use": "hour_sin = sin(2*pi*h/24), hour_cos = cos(2*pi*h/24)",
    },
    {
        "name": "day",
        "type": "categorical",
        "allowed": DAYS,
        "twin_signal": "Simulation clock of the twin (day of week)",
        "model_use": "one-hot, 7 columns (WeekStatus is derivable from it and is not used)",
    },
    {
        "name": "load_type",
        "type": "categorical",
        "allowed": LOAD_TYPES,
        "twin_signal": "SAG mill tonnage divided by nominal tonnage",
        "rule": {
            "Light_Load": "ratio < 0.75",
            "Medium_Load": "0.75 <= ratio <= 0.90",
            "Maximum_Load": "ratio > 0.90",
            "thresholds": dict(LOAD_THRESHOLDS),
        },
        "model_use": "one-hot, 3 columns",
    },
]

# Variables studied in the lab but never sent to the model.
EXCLUDED = [
    {"name": "Lagging_Current_Reactive.Power_kVarh", "reason": "Analysed in the lab only; the twin cannot produce it."},
    {"name": "Leading_Current_Reactive_Power_kVarh", "reason": "Analysed in the lab only; the twin cannot produce it."},
    {"name": "Lagging_Current_Power_Factor", "reason": "Analysed in the lab only; the twin cannot produce it."},
    {"name": "Leading_Current_Power_Factor", "reason": "Analysed in the lab only; the twin cannot produce it."},
    {"name": "NSM", "reason": "Seconds since midnight; redundant with the hour of day."},
    {"name": "WeekStatus", "reason": "Derivable from day of week."},
    {"name": "CO2(tCO2)", "reason": "Almost a copy of consumption (VIF); computed afterwards from kWh."},
]

PREPROCESSING = {
    "interval_convention": (
        "The file stamps the END of each 15-min interval. Features use the interval START "
        "(end - 15 min); the 00:00 record closes the previous day."
    ),
    "features": feature_names(),
    "elastic_net": "ColumnTransformer (one-hot + sin/cos) -> StandardScaler -> ElasticNet",
    "trees": "ColumnTransformer (one-hot + sin/cos passthrough) -> RandomForest / XGBoost, no scaling",
    "seed": SEED,
}


def contract_table_rows() -> list[dict]:
    """Rows for the Negocio screen table (Spanish labels)."""
    rows = [
        {"variable": "Usage_kWh", "rol": "Objetivo",
         "unidad / valores": UNIT, "señal del gemelo": "Salida: kWh de la planta cada 15 min"},
        {"variable": "hour", "rol": "Entrada",
         "unidad / valores": "0 a 23.75 (se codifica como seno y coseno)",
         "señal del gemelo": "Reloj de simulación"},
        {"variable": "day", "rol": "Entrada",
         "unidad / valores": "Lunes a Domingo",
         "señal del gemelo": "Reloj de simulación"},
        {"variable": "load_type", "rol": "Entrada",
         "unidad / valores": "Light / Medium / Maximum",
         "señal del gemelo": "Tonelaje SAG / nominal: menor a 75 % ligera, hasta 90 % media, mayor a 90 % máxima"},
    ]
    for e in EXCLUDED:
        rows.append({
            "variable": e["name"],
            "rol": "Solo laboratorio" if "Analysed" in e["reason"] else "Excluida",
            "unidad / valores": "-",
            "señal del gemelo": "No la produce el gemelo" if "Analysed" in e["reason"]
            else ("Derivable del reloj" if "Derivable" in e["reason"] or "redundant" in e["reason"]
                  else "Se calcula después desde kWh"),
        })
    return rows


def variable_contract() -> dict:
    """Contract block embedded in the exported JSON."""
    return {
        "target": TARGET,
        "inputs": INPUTS,
        "excluded": EXCLUDED,
        "preprocessing": PREPROCESSING,
    }
