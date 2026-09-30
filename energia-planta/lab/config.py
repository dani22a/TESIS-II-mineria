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
LOAD_SHORT = {"Light_Load": "Ligera", "Medium_Load": "Media", "Maximum_Load": "Máxima"}
# One color per load type and per model, shared by every figure (see lab/theme.py).
LOAD_COLORS = {"Light_Load": "#2E86AB", "Medium_Load": "#E8A33D", "Maximum_Load": "#C8453F"}

# Twin rule: SAG tonnage / nominal tonnage -> load type.
LOAD_THRESHOLDS = {"medium_from": 0.75, "maximum_above": 0.90}

MODELS = ["Elastic Net", "Random Forest", "XGBoost"]
MODEL_COLORS = {"Elastic Net": "#8A8F98", "Random Forest": "#2F9E74", "XGBoost": "#4B4FD8"}

# Navigation metadata. "key" is the stable session value; everything else is display copy.
PHASE_META = [
    {"key": "1. Negocio", "label": "1 · Negocio", "title": "Negocio",
     "subtitle": "¿Qué queremos predecir?",
     "next": "Revisar la calidad de los datos antes de usarlos."},
    {"key": "2. Datos", "label": "2 · Datos", "title": "Datos",
     "subtitle": "¿Son confiables los registros?",
     "next": "Explorar el consumo con gráficos para ver patrones."},
    {"key": "3. EDA", "label": "3 · EDA", "title": "Análisis exploratorio (EDA)",
     "subtitle": "¿Qué patrones hay en el consumo?",
     "next": "Confirmar con pruebas estadísticas qué variables entran al modelo."},
    {"key": "4. Pruebas", "label": "4 · Pruebas", "title": "Pruebas estadísticas",
     "subtitle": "¿Qué variables entran al modelo?",
     "next": "Preparar las variables y el corte temporal entre entrenamiento y examen."},
    {"key": "5. Preparación", "label": "5 · Preparación", "title": "Preparación de datos",
     "subtitle": "¿Cómo se arman las entradas?",
     "next": "Buscar los mejores hiperparámetros de cada modelo con validación temporal."},
    {"key": "6. Modelado", "label": "6 · Modelado", "title": "Modelado",
     "subtitle": "¿Cómo se ajusta cada modelo?",
     "next": "Medir los tres modelos en el examen y explicar sus resultados."},
    {"key": "7. Evaluación", "label": "7 · Evaluación", "title": "Evaluación",
     "subtitle": "¿Qué modelo se equivoca menos y por qué?",
     "next": "Probar escenarios con el modelo elegido y descargar el artefacto para el gemelo."},
    {"key": "8. Despliegue", "label": "8 · Despliegue", "title": "Despliegue",
     "subtitle": "¿Qué recibe el gemelo digital?",
     "next": ""},
]
PHASES = [m["key"] for m in PHASE_META]
