"""Phase 8 - Despliegue: manual scenario and download of the JSON the twin reads."""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import export
from lab.config import DAYS, DAYS_ES, FINAL_ARTIFACT, LOAD_COLORS, LOAD_ES, LOAD_SHORT, LOAD_TYPES
from lab.glossary import help_text
from lab.theme import NEUTRAL, style_fig
from lab.ui import (glossary_expander, next_step, not_trained_message, page_header, reading, show_fig,
                    train_all_button)

PURPOSE = ("Prueba el modelo elegido con un escenario de hora, día y tipo de carga, y descarga el archivo "
           "que el gemelo digital lee para mostrar el consumo esperado de la planta.")


def render() -> None:
    art = export.load_artifact()
    if art is None:
        page_header(8, PURPOSE, [("Modelo exportado", "Sin exportar", "El artefacto se genera al entrenar."),
                                 ("MAE en el examen", "-", help_text("MAE")),
                                 ("Filas de predicción", "-", "Combinaciones de hora, día y tipo de carga que el gemelo puede consultar."),
                                 ("Escenarios explicados", "-", "Casos típicos con una frase que explica la predicción.")])
        not_trained_message("El despliegue")
        train_all_button("btn_deploy", expanded=True)
        glossary_expander(["MAE", "SHAP"], "Glosario")
        next_step(8)
        return

    exam = art["exam_metrics"]["per_model"][art["model"]]
    page_header(8, PURPOSE, [
        ("Modelo exportado", art["model"], "El de menor MAE en el examen."),
        ("MAE en el examen", f"{exam['mae']:.2f} kWh", help_text("MAE")),
        ("Filas de predicción", f"{len(art['prediction_table']):,}", "Combinaciones de hora, día y tipo de carga que el gemelo puede consultar."),
        ("Escenarios explicados", len(art["scenario_explanations"]), "Casos típicos con una frase que explica la predicción."),
    ])
    problems = export.validate_artifact(art)
    if problems:
        st.error("El artefacto no cumple el esquema: " + "; ".join(problems), icon=":material/error:")
    else:
        st.success("El artefacto cumple el esquema que espera el gemelo digital.", icon=":material/check_circle:")

    st.subheader("Paso 1 · Elija un escenario")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        hour = c1.slider("Hora del día (inicio del intervalo)", 0, 23, 14)
        day = c2.selectbox("Día de la semana", DAYS, index=2, format_func=lambda d: DAYS_ES[d])
        load = c3.radio("Tipo de carga", LOAD_TYPES, index=2, format_func=lambda t: LOAD_SHORT[t], horizontal=True,
                        help="Ligera, media o máxima, según el tonelaje del molino SAG frente al nominal.")

    st.subheader("Paso 2 · Vea la predicción y su explicación")
    kwh = export.lookup_kwh(art, hour, day, load)
    co2 = export.co2_from_kwh(art, kwh)
    m1, m2, m3 = st.columns(3)
    m1.metric("Consumo previsto", f"{kwh:.2f} kWh / 15 min", border=True,
              help="Energía que el modelo espera para el intervalo de 15 minutos que empieza a la hora elegida.")
    m2.metric("Potencia media equivalente", f"{kwh * 4:.1f} kW", border=True,
              help="El consumo de 15 minutos multiplicado por 4 equivale a una potencia promedio en kW.")
    m3.metric("CO2 (calculado después)", f"{co2:.4f} tCO2 / 15 min", border=True,
              help="El modelo no predice el CO2: se calcula multiplicando los kWh por un factor obtenido de los datos.")
    st.caption(
        "El CO2 es una cifra calculada después, no una predicción: se obtiene multiplicando los kWh por el factor "
        f"{art['variable_contract']['post_computed']['co2_tco2']['factor_tco2_per_kwh']:.6f} tCO2/kWh obtenido de los datos."
    )
    scenario, exact = export.lookup_explanation(art, hour, day, load)
    if scenario:
        st.markdown(f"**Explicación{'' if exact else ' (escenario típico más cercano: ' + str(scenario['hour']) + ' h)'}.** {scenario['phrase']}")

    curve = [export.lookup_kwh(art, h, day, load) for h in range(24)]
    fig = go.Figure(go.Bar(x=list(range(24)), y=curve, marker_color=[LOAD_COLORS[load] if h == hour else NEUTRAL for h in range(24)],
                           hovertemplate="%{x:02d}:00 h: %{y:.2f} kWh<extra></extra>"))
    style_fig(fig, f"Consumo esperado a lo largo del día: {DAYS_ES[day].lower()}, carga {LOAD_SHORT[load].lower()}",
              x="Hora del día (la barra de color es la hora elegida)", y="Consumo (kWh / 15 min)", height=340, legend=False)
    fig.update_layout(margin=dict(t=64))
    fig.update_xaxes(dtick=2)
    show_fig(fig)
    peak_h = int(pd.Series(curve).idxmax())
    reading(
        f"Para {DAYS_ES[day].lower()} con {LOAD_ES[load].lower()}, el modelo {art['model']} prevé {kwh:.1f} kWh a las {hour:02d}:00; el máximo del día es "
        f"{max(curve):.1f} kWh a las {peak_h:02d}:00 y el mínimo {min(curve):.1f} kWh.",
        "La barra resaltada es la hora elegida; el resto muestra cómo cambiaría el consumo esperado si el turno cambiara de hora, con el mismo día y tipo de carga.",
        "El gemelo usa esta misma tabla: dado el reloj y la razón tonelaje SAG sobre nominal, muestra la electricidad esperada de la planta cada 15 min.",
    )
    _typical_scenarios(art)

    st.subheader("Paso 3 · Descargue el artefacto")
    payload = json.dumps(art, indent=2, ensure_ascii=False).encode("utf-8")
    st.download_button("Descargar planta_xgboost.json", data=payload, file_name=FINAL_ARTIFACT.name, mime="application/json",
                       icon=":material/download:", type="primary")
    reading(
        f"Un JSON de {len(payload) / 1024:.0f} KB con el contrato de variables, los hiperparámetros congelados, las métricas del examen, "
        f"{len(art['prediction_table'])} filas de predicción y las frases de explicación.",
        "El gemelo no ejecuta Python: lee este archivo y busca el kWh por hora, día y tipo de carga.",
        "Al reentrenar con datos nuevos se regenera el archivo; el gemelo lo recoge sin cambiar de código.",
    )
    train_all_button("btn_deploy")
    glossary_expander(["MAE", "SHAP"], "Glosario")
    next_step(8)


def _typical_scenarios(art: dict) -> None:
    with st.expander("Escenarios típicos explicados por el modelo", icon=":material/list_alt:"):
        sc = pd.DataFrame(art["scenario_explanations"])
        sc["día"] = sc["day"].map(DAYS_ES)
        sc["carga"] = sc["load_type"].map(LOAD_SHORT)
        st.dataframe(sc[["hour", "día", "carga", "kwh", "phrase"]].rename(
            columns={"hour": "Hora", "día": "Día", "carga": "Tipo de carga", "kwh": "Consumo (kWh / 15 min)", "phrase": "Explicación"}),
            hide_index=True, width="stretch")
        hi = sc.loc[sc["kwh"].idxmax()]
        lo = sc.loc[sc["kwh"].idxmin()]
        reading(
            f"{len(sc)} escenarios típicos: el mayor es carga {hi['carga'].lower()}, {hi['día'].lower()} a las {hi['hour']:02d}:00 con {hi['kwh']:.1f} kWh y el menor "
            f"carga {lo['carga'].lower()}, {lo['día'].lower()} a las {lo['hour']:02d}:00 con {lo['kwh']:.1f} kWh.",
            "Cada frase parte del promedio de la planta y reparte la diferencia entre carga, hora y día con valores SHAP de XGBoost, por lo que el gemelo "
            "puede explicar sin recalcular nada.",
            "El operador puede citar la frase del escenario más parecido cuando el gemelo muestre un consumo inusual.",
        )
