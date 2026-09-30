"""Phase 3 - EDA: annual series, hourly profile, boxes, Spearman matrix and CO2 vs kWh."""
from __future__ import annotations

import streamlit as st

from lab import eda
from lab.stats_tests import spearman_matrix
from lab.ui import load_data, reading, require_data


@st.cache_data(show_spinner="Construyendo figuras...")
def _figures():
    _, df = load_data()
    return {
        "series": eda.figure_series(df),
        "profile": eda.figure_profile(df),
        "box_load": eda.figure_box_load(df),
        "box_day": eda.figure_box_day(df),
        "spearman": eda.figure_spearman(spearman_matrix(df)),
        "co2": eda.figure_co2(df),
    }


def render() -> None:
    st.header("3. EDA")
    if require_data() is None:
        return
    figs = _figures()
    sections = [
        ("Serie del año completo", "series"),
        ("Perfil medio por hora y tipo de carga", "profile"),
        ("Consumo por tipo de carga", "box_load"),
        ("Consumo por día de la semana", "box_day"),
        ("Matriz de Spearman", "spearman"),
        ("El CO2 copia al consumo", "co2"),
    ]
    for title, key in sections:
        st.subheader(title)
        fig, text = figs[key]
        st.plotly_chart(fig, width="stretch")
        reading(*text)
