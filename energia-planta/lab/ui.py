"""Streamlit helpers: the three-line reading, cached loaders and artifact I/O."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from .config import ARTIFACTS, DATA_PATH
from . import data as data_mod


def reading(see: str, meaning: str, decision: str) -> None:
    """Render the three fixed lines shown under every figure and table."""
    with st.container(border=True):
        st.markdown(f"**Qué se ve.** {see}")
        st.markdown(f"**Qué significa.** {meaning}")
        st.markdown(f"**Qué decisión permite en la planta.** {decision}")


def data_available() -> bool:
    return DATA_PATH.exists()


@st.cache_data(show_spinner="Cargando datos...")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (raw, prepared) frames; cached across reruns."""
    raw = data_mod.load_raw()
    return raw, data_mod.prepare(raw)


@st.cache_data(show_spinner="Calculando reporte de calidad...")
def load_quality() -> dict:
    raw, df = load_data()
    return data_mod.quality_report(raw, df)


def require_data() -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Load the data or show a friendly message and return None."""
    if not data_available():
        st.error(
            f"No se encontró el archivo de datos en `{DATA_PATH}`. "
            "Coloque `Steel_industry_data.csv` en la carpeta `data/` (no se versiona)."
        )
        return None
    return load_data()


def read_json(name: str):
    """Read a JSON artifact from artefactos/, or None when it does not exist."""
    path = ARTIFACTS / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def not_trained_message(what: str = "Esta pantalla") -> None:
    st.info(
        f"{what} aún no tiene resultados: el modelo no ha sido entrenado. "
        "Ejecute `python train.py` o use el botón de entrenamiento."
    )


def fmt(x: float, digits: int = 1) -> str:
    return f"{x:,.{digits}f}"
