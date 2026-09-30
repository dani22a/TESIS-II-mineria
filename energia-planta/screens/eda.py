"""Phase 3 - EDA: annual series, hourly profile, boxes, Spearman matrix and CO2 vs kWh."""
from __future__ import annotations

import streamlit as st

from lab import eda
from lab.config import TARGET
from lab.glossary import help_text
from lab.stats_tests import spearman_matrix
from lab.ui import glossary_expander, load_data, next_step, page_header, reading, require_data, show_fig

PURPOSE = "Muestra con gráficos cómo varía el consumo según el mes, la hora, el día y el tipo de carga."


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


def _block(figs: dict, key: str) -> None:
    fig, text = figs[key]
    show_fig(fig)
    reading(*text)


def render() -> None:
    if require_data(3, PURPOSE) is None:
        return
    _, df = load_data()
    figs = _figures()
    co2_corr = df[TARGET].corr(df["CO2(tCO2)"])
    page_header(3, PURPOSE, [
        ("Consumo medio", f"{df[TARGET].mean():.1f} kWh", "Promedio del consumo por intervalo de 15 minutos durante el año."),
        ("Consumo máximo", f"{df[TARGET].max():.0f} kWh", "Mayor consumo observado en un intervalo de 15 minutos."),
        ("Intervalos de bajo consumo", f"{(df[TARGET] < 5).mean() * 100:.0f} %", "Parte de los registros con menos de 5 kWh (planta ligera o detenida)."),
        ("Correlación CO2 y consumo", f"{co2_corr:.3f}", "Correlación de Pearson: cerca de 1 significa que ambas series se mueven casi igual."),
    ])

    tab_s, tab_h, tab_l, tab_c = st.tabs(["Año completo", "Hora y día", "Tipo de carga", "Correlaciones y CO2"])
    with tab_s:
        _block(figs, "series")
    with tab_h:
        _block(figs, "profile")
        _block(figs, "box_day")
    with tab_l:
        _block(figs, "box_load")
    with tab_c:
        _block(figs, "spearman")
        _block(figs, "co2")
    glossary_expander(["Spearman"], "Glosario: correlación")
    next_step(3)
