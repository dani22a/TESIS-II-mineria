"""Phase 1 - Negocio: question, unit and variable contract."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from lab import contract
from lab.config import LOAD_COLORS, LOAD_ES, LOAD_TYPES, TARGET, UNIT
from lab.ui import fmt, reading, require_data


def render() -> None:
    st.header("1. Negocio")
    st.markdown(
        "**Pregunta de negocio.** Conociendo la hora, el día y el tipo de carga, "
        "¿cuántos kWh consumirá la planta en los próximos 15 minutos y cuál de los tres "
        "modelos (Elastic Net, Random Forest, XGBoost) se equivoca menos?"
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Objetivo", TARGET)
    col2.metric("Unidad", UNIT)
    col3.metric("Métrica principal", "MAE (kWh)")

    st.markdown(
        "El laboratorio entrena y compara; el gemelo digital solo consume el artefacto exportado "
        "(`artefactos/planta_xgboost.json`) y muestra la electricidad de la planta cada 15 min. "
        "El modelo exportado usa **únicamente** señales que el gemelo puede producir."
    )

    st.subheader("Contrato de variables")
    st.dataframe(pd.DataFrame(contract.contract_table_rows()), hide_index=True, width="stretch")

    loaded = require_data()
    if loaded is None:
        reading(
            "Una tabla con tres variables de entrada, un objetivo y las variables que se quedan fuera.",
            "El contrato fija qué señal del gemelo alimenta cada variable del modelo.",
            "Antes de entrenar, se confirma que el gemelo puede producir hora, día y tipo de carga; "
            "lo demás no se exige.",
        )
        return
    _, df = loaded
    n_in = len(contract.INPUTS)
    n_out = len(contract.EXCLUDED)
    reading(
        f"{n_in} variables de entrada (hora, día, tipo de carga), 1 objetivo y {n_out} columnas del archivo "
        "que quedan fuera del modelo (potencia reactiva, factor de potencia, NSM, WeekStatus y CO2).",
        "Cada entrada tiene una fuente concreta en el gemelo: el reloj de simulación para hora y día, y la razón "
        "tonelaje SAG sobre nominal para el tipo de carga (menor a 75 % ligera, hasta 90 % media, mayor a 90 % máxima). "
        "El CO2 no entra porque se obtiene a partir de los kWh.",
        "El gemelo puede alimentar el modelo sin sensores nuevos; reactiva y factor de potencia se estudian "
        "solo para entender el archivo, no para predecir.",
    )

    st.subheader("Consumo típico por tipo de carga")
    stats = df.groupby("Load_Type")[TARGET].agg(["mean", "median", "count"]).reindex(LOAD_TYPES).reset_index()
    stats["Tipo de carga"] = stats["Load_Type"].map(LOAD_ES)
    fig = px.bar(
        stats, x="Tipo de carga", y="mean", color="Load_Type", color_discrete_map=LOAD_COLORS,
        labels={"mean": "kWh medios por 15 min"}, template="plotly_white",
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")
    m = stats.set_index("Load_Type")
    ratio = m.loc["Maximum_Load", "mean"] / m.loc["Light_Load", "mean"]
    reading(
        f"El consumo medio por 15 min es {fmt(m.loc['Light_Load', 'mean'])} kWh en carga ligera, "
        f"{fmt(m.loc['Medium_Load', 'mean'])} kWh en media y {fmt(m.loc['Maximum_Load', 'mean'])} kWh en máxima "
        f"({fmt(ratio)} veces entre extremos).",
        "El tipo de carga separa regímenes de consumo muy distintos, por lo que es la señal del gemelo con "
        "más peso esperado en la predicción.",
        "Cuando el tonelaje SAG cruce el 75 % o el 90 % del nominal, el gemelo debe esperar un salto de "
        "consumo y puede anticipar la demanda eléctrica.",
    )
