"""Phase 8 - Despliegue: manual scenario and download of the JSON the twin reads."""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import export
from lab.config import DAYS, DAYS_ES, FINAL_ARTIFACT, LOAD_COLORS, LOAD_ES, LOAD_TYPES
from lab.ui import not_trained_message, reading, train_all_button


def render() -> None:
    st.header("8. Despliegue")
    art = export.load_artifact()
    if art is None:
        not_trained_message("El despliegue")
        train_all_button("btn_deploy")
        return

    problems = export.validate_artifact(art)
    if problems:
        st.error("El artefacto no cumple el esquema: " + "; ".join(problems))
    else:
        st.success(
            f"Artefacto válido: modelo {art['model']}, {len(art['prediction_table'])} filas en la tabla de predicción "
            f"y {len(art['scenario_explanations'])} escenarios explicados."
        )

    st.subheader("Escenario manual")
    c1, c2, c3 = st.columns(3)
    hour = c1.slider("Hora del día", 0, 23, 14)
    day = c2.selectbox("Día de la semana", DAYS, index=2, format_func=lambda d: DAYS_ES[d])
    load = c3.radio("Tipo de carga", LOAD_TYPES, index=2, format_func=lambda t: LOAD_ES[t], horizontal=True)

    kwh = export.lookup_kwh(art, hour, day, load)
    co2 = export.co2_from_kwh(art, kwh)
    m1, m2, m3 = st.columns(3)
    m1.metric("Consumo previsto", f"{kwh:.2f} kWh / 15 min")
    m2.metric("Potencia media equivalente", f"{kwh * 4:.1f} kW")
    m3.metric("CO2 calculado después desde kWh", f"{co2:.4f} tCO2 / 15 min")
    st.caption(
        "El CO2 no lo predice el modelo: se calcula multiplicando los kWh por el factor "
        f"{art['variable_contract']['post_computed']['co2_tco2']['factor_tco2_per_kwh']:.6f} tCO2/kWh obtenido de los datos."
    )
    scenario, exact = export.lookup_explanation(art, hour, day, load)
    if scenario:
        st.markdown(f"**Explicación{'' if exact else ' (escenario típico más cercano: ' + str(scenario['hour']) + ' h)'}.** {scenario['phrase']}")

    curve = [export.lookup_kwh(art, h, day, load) for h in range(24)]
    fig = go.Figure(go.Bar(x=list(range(24)), y=curve, marker_color=[LOAD_COLORS[load] if h == hour else "#c9d3e0" for h in range(24)]))
    fig.update_layout(template="plotly_white", height=320, xaxis_title="Hora del día", yaxis_title="kWh por 15 min", xaxis=dict(dtick=2))
    st.plotly_chart(fig, width="stretch")
    peak_h = int(pd.Series(curve).idxmax())
    reading(
        f"Para {DAYS_ES[day].lower()} con {LOAD_ES[load].lower()}, el modelo {art['model']} prevé {kwh:.1f} kWh a las {hour:02d}:00; el máximo del día es "
        f"{max(curve):.1f} kWh a las {peak_h:02d}:00 y el mínimo {min(curve):.1f} kWh.",
        "La barra resaltada es la hora elegida; el resto muestra cómo cambiaría el consumo esperado si el turno cambiara de hora, con el mismo día y tipo de carga.",
        "El gemelo usa esta misma tabla: dado el reloj y la razón tonelaje SAG sobre nominal, muestra la electricidad esperada de la planta cada 15 min.",
    )

    st.subheader("Escenarios típicos explicados")
    sc = pd.DataFrame(art["scenario_explanations"])
    sc["día"] = sc["day"].map(DAYS_ES)
    sc["carga"] = sc["load_type"].map(LOAD_ES)
    st.dataframe(sc[["hour", "día", "carga", "kwh", "phrase"]].rename(columns={"hour": "hora", "kwh": "kWh", "phrase": "frase"}),
                 hide_index=True, width="stretch")
    hi = sc.loc[sc["kwh"].idxmax()]
    lo = sc.loc[sc["kwh"].idxmin()]
    reading(
        f"{len(sc)} escenarios típicos: el mayor es {hi['carga'].lower()}, {hi['día'].lower()} a las {hi['hour']:02d}:00 con {hi['kwh']:.1f} kWh y el menor "
        f"{lo['carga'].lower()}, {lo['día'].lower()} a las {lo['hour']:02d}:00 con {lo['kwh']:.1f} kWh.",
        "Cada frase parte del promedio de la planta y reparte la diferencia entre carga, hora y día con valores SHAP de XGBoost, por lo que el gemelo "
        "puede explicar sin recalcular nada.",
        "El operador puede citar la frase del escenario más parecido cuando el gemelo muestre un consumo inusual.",
    )

    st.subheader("Descarga del artefacto")
    payload = json.dumps(art, indent=2, ensure_ascii=False).encode("utf-8")
    st.download_button("Descargar planta_xgboost.json", data=payload, file_name=FINAL_ARTIFACT.name, mime="application/json")
    reading(
        f"Un JSON de {len(payload) / 1024:.0f} KB con el contrato de variables, los hiperparámetros congelados, las métricas del examen, "
        f"{len(art['prediction_table'])} filas de predicción y las frases de explicación.",
        "El gemelo no ejecuta Python: lee este archivo y busca el kWh por hora, día y tipo de carga.",
        "Al reentrenar con datos nuevos se regenera el archivo; el gemelo lo recoge sin cambiar de código.",
    )
    train_all_button("btn_deploy")
