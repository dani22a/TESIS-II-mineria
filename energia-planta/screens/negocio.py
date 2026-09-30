"""Phase 1 - Negocio: question, unit and variable contract."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from lab import contract
from lab.config import LOAD_COLORS, LOAD_SHORT, LOAD_TYPES, MODELS, TARGET
from lab.glossary import help_text
from lab.theme import style_fig
from lab.ui import fmt, glossary_expander, next_step, page_header, reading, require_data, show_fig

PURPOSE = (
    "Define qué se quiere predecir, con qué información y cómo se medirá el error, "
    "para que el resto del laboratorio responda a una pregunta concreta."
)


def render() -> None:
    page_header(1, PURPOSE, [
        ("Qué se predice", "Consumo", "Energía eléctrica que consume la planta en cada intervalo."),
        ("Unidad", "kWh / 15 min", "Kilovatios-hora consumidos en cada intervalo de 15 minutos."),
        ("Entradas del modelo", f"{len(contract.INPUTS)} variables", "Hora del día, día de la semana y tipo de carga."),
        ("Métrica principal", "MAE (kWh)", help_text("MAE")),
    ])

    tab_q, tab_c, tab_l = st.tabs(["Pregunta y alcance", "Contrato de variables", "Consumo por tipo de carga"])

    with tab_q:
        st.markdown(
            "**Pregunta de negocio.** Conociendo la hora, el día y el tipo de carga, "
            f"¿cuántos kWh consumirá la planta en los próximos 15 minutos y cuál de los tres modelos ({', '.join(MODELS)}) "
            "se equivoca menos?"
        )
        st.markdown(
            "El laboratorio entrena y compara; el gemelo digital solo consume el artefacto exportado "
            "(`artefactos/planta_xgboost.json`) y muestra la electricidad de la planta cada 15 min. "
            "El modelo exportado usa **únicamente** señales que el gemelo puede producir."
        )

    with tab_c:
        st.dataframe(
            pd.DataFrame(contract.contract_table_rows()).rename(columns={
                "variable": "Variable", "rol": "Rol", "unidad / valores": "Unidad o valores",
                "señal del gemelo": "Señal del gemelo digital"}),
            hide_index=True, width="stretch")
        n_out = len(contract.EXCLUDED)
        reading(
            f"{len(contract.INPUTS)} variables de entrada (hora, día, tipo de carga), 1 objetivo y {n_out} columnas del archivo "
            "que quedan fuera del modelo (potencia reactiva, factor de potencia, NSM, WeekStatus y CO2).",
            "Cada entrada tiene una fuente concreta en el gemelo: el reloj de simulación para hora y día, y la razón "
            "tonelaje SAG sobre nominal para el tipo de carga (menor a 75 % ligera, hasta 90 % media, mayor a 90 % máxima). "
            "El CO2 no entra porque se obtiene a partir de los kWh.",
            "El gemelo puede alimentar el modelo sin sensores nuevos; reactiva y factor de potencia se estudian "
            "solo para entender el archivo, no para predecir.",
        )

    with tab_l:
        _load_tab()

    glossary_expander(["MAE", "MAPE", "RMSE"], "Glosario: métricas de error")
    next_step(1)


def _load_tab() -> None:
    loaded = require_data()
    if loaded is None:
        return
    _, df = loaded
    stats = df.groupby("Load_Type")[TARGET].agg(["mean", "median", "count"]).reindex(LOAD_TYPES).reset_index()
    stats["Tipo de carga"] = stats["Load_Type"].map(LOAD_SHORT)
    fig = px.bar(stats, x="Tipo de carga", y="mean", color="Load_Type", color_discrete_map=LOAD_COLORS,
                 text=stats["mean"].round(1), labels={"mean": "Consumo medio"})
    fig.update_traces(textposition="outside", hovertemplate="%{x}: %{y:.1f} kWh / 15 min<extra></extra>")
    style_fig(fig, "Consumo medio según el tipo de carga", x="Tipo de carga",
              y="Consumo medio (kWh / 15 min)", legend=False)
    show_fig(fig)
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
