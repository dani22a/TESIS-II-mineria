"""Shared constants: paths, seed, labels and the CRISP-DM phase list."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "Steel_industry_data.csv"
ARTIFACTS = ROOT / "artefactos"
FINAL_ARTIFACT = ARTIFACTS / "planta_xgboost.json"

SEED = 42
TARGET = "Usage_kWh"
UNIT = "kWh/15min"
INTERVAL_MIN = 15

# The exam is the last quarter (Oct-Dec). Splits use the interval START time.
EXAM_START = pd.Timestamp("2018-10-01 00:00:00")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAYS_ES = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo",
}
LOAD_TYPES = ["Light_Load", "Medium_Load", "Maximum_Load"]
LOAD_ES = {"Light_Load": "Carga ligera", "Medium_Load": "Carga media", "Maximum_Load": "Carga máxima"}
LOAD_COLORS = {"Light_Load": "#4c9be8", "Medium_Load": "#f2a541", "Maximum_Load": "#d64550"}

# Twin rule: SAG tonnage / nominal tonnage -> load type.
LOAD_THRESHOLDS = {"medium_from": 0.75, "maximum_above": 0.90}

MODELS = ["Elastic Net", "Random Forest", "XGBoost"]

PHASES = [
    "1. Negocio",
    "2. Datos",
    "3. EDA",
    "4. Pruebas",
    "5. Preparación",
    "6. Modelado",
    "7. Evaluación",
    "8. Despliegue",
]
