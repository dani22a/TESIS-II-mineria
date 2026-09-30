"""Phase 2 - Datos: quality report (rows, 15-min gaps, duplicates, ranges)."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from lab.ui import fmt, load_quality, reading, require_data


def render() -> None:
    st.header("2. Datos")
    loaded = require_data()
    if loaded is None:
        return
    raw, df = loaded
    q = load_quality()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas", f"{q['n_rows']:,}")
    c2.metric("Columnas", q["n_cols"])
    c3.metric("Slots de 15 min faltantes", q["n_missing"])
    c4.metric("Duplicados", q["ts_duplicates"] + q["raw_duplicate_labels"])

    st.subheader("Lectura de la fecha y convención del intervalo")
    st.markdown(
        f"La columna `date` (formato `dd/mm/YYYY HH:MM`) se interpretó sin fallos ({q['parse_failures']} errores). "
        "El archivo marca el **final** de cada intervalo de 15 min. El registro de medianoche (NSM = 0) lleva la "
        "fecha del día que cierra y no la del siguiente, por lo que el orden crudo retrocede "
        f"{q['raw_out_of_order']} veces. Se reconstruye `ts_end = día + NSM` (más un día si NSM = 0) y "
        "`ts_start = ts_end - 15 min`; el modelo y el corte temporal usan el inicio del intervalo."
    )
    reading(
        f"{q['midnight_records']} registros de medianoche con la fecha del día que cierran; tras reconstruir, "
        f"la serie va de {q['ts_end_min']:%d/%m/%Y %H:%M} a {q['ts_end_max']:%d/%m/%Y %H:%M}.",
        "Sin la reconstrucción, cada día tendría un hueco a las 00:15 y un duplicado ficticio a las 00:00; "
        "con ella la serie es continua y cada registro pertenece al intervalo correcto.",
        "Toda hora usada por el modelo y por el gemelo se calcula sobre el inicio del intervalo, de modo que "
        "el kWh de las 14:00 significa la energía consumida entre las 14:00 y las 14:15.",
    )

    st.subheader("Completitud de la serie de 15 min")
    exp = q["monthly"]
    fig = go.Figure()
    fig.add_bar(x=exp["mes"], y=exp["registros"], name="Registros")
    fig.add_scatter(x=exp["mes"], y=exp["esperados"], name="Esperados", mode="markers",
                    marker=dict(symbol="diamond", size=9, color="#d64550"))
    fig.update_layout(template="plotly_white", yaxis_title="Registros por mes", height=340)
    st.plotly_chart(fig, width="stretch")
    all_match = bool((exp["registros"] == exp["esperados"]).all())
    reading(
        f"Se esperan {q['n_expected']:,} slots entre el primer y el último registro y hay {q['n_rows']:,}: "
        f"faltan {q['n_missing']} y hay {q['ts_duplicates']} timestamps repetidos. "
        + ("Todos los meses coinciden con lo esperado." if all_match else "Hay meses que no coinciden con lo esperado."),
        "La reconstrucción del rango completo confirma que el año está entero, sin huecos que rellenar "
        "ni registros que descartar." if q["n_missing"] == 0 and q["ts_duplicates"] == 0
        else "Existen huecos o repetidos que deben tratarse antes de modelar.",
        "Se puede validar en el tiempo sin imputar: las ventanas de entrenamiento y examen son continuas."
        if q["n_missing"] == 0 else "Antes de entrenar hay que decidir cómo tratar los slots faltantes.",
    )
    st.dataframe(q["gaps"].rename(columns={"gap": "diferencia entre registros", "records": "registros"}),
                 hide_index=True)
    only15 = len(q["gaps"]) == 1
    reading(
        "Distribución de la diferencia entre registros consecutivos tras reconstruir el tiempo: "
        + ", ".join(f"{r.gap} en {r.records:,}" for r in q["gaps"].itertuples()) + ".",
        "Toda la serie avanza en pasos de 15 minutos exactos." if only15 else "Hay saltos distintos de 15 min.",
        "El intervalo de 15 min es la resolución natural del gemelo; no se requiere remuestreo."
        if only15 else "Revisar los saltos antes de usar ventanas temporales.",
    )

    st.subheader("Tipos de dato")
    st.dataframe(q["dtypes"], hide_index=True)
    reading(
        f"{q['n_cols']} columnas con {q['nulls_total']} valores nulos en total; las variables numéricas se leen "
        "como decimales o enteros y las de calendario como texto.",
        "No hay nulos que imputar; el texto de calendario (día, tipo de carga) se codificará en la preparación.",
        "No se requiere ninguna limpieza previa; el procesamiento se limita a codificar hora, día y tipo de carga.",
    )

    st.subheader("Rangos y validez")
    st.dataframe(q["ranges"], hide_index=True, width="stretch")
    bad = int(q["ranges"]["fuera de rango"].sum())
    ck = q["checks"]
    reading(
        f"{bad} valores fuera de la regla de validez. {q['zero_kwh']} registro(s) con consumo exactamente cero. "
        f"Coherencia de calendario: {ck['day_matches_label']:,} de {q['n_rows']:,} filas con el día de la semana "
        f"igual al del inicio del intervalo y {ck['weekstatus_consistent']:,} con WeekStatus consistente.",
        "Los rangos son físicamente plausibles (factores de potencia entre 0 y 100, energías no negativas) "
        "y el calendario del archivo es coherente con el reloj reconstruido."
        if bad == 0 else "Hay valores fuera de rango que deben revisarse.",
        f"Los ceros de reactiva ({fmt(q['ranges'].set_index('variable').loc['Lagging_Current_Reactive.Power_kVarh', 'ceros'], 0)} "
        "filas en la lagging) son normales cuando la planta está ligera; no se eliminan filas.",
    )
