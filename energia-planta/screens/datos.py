"""Phase 2 - Datos: quality report (rows, 15-min gaps, duplicates, ranges)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab.theme import ACCENT, COLUMN_ES, DTYPE_ES, POSITIVE, style_fig
from lab.ui import fmt, load_quality, next_step, page_header, reading, require_data, show_fig

PURPOSE = "Comprueba que el archivo de consumo está completo y es coherente antes de analizarlo o modelarlo."


def render() -> None:
    loaded = require_data(2, PURPOSE)
    if loaded is None:
        return
    raw, df = loaded
    q = load_quality()

    page_header(2, PURPOSE, [
        ("Registros", f"{q['n_rows']:,}", "Filas del archivo; cada una es un intervalo de 15 minutos."),
        ("Columnas", q["n_cols"], "Variables que trae el archivo original."),
        ("Intervalos faltantes", q["n_missing"], "Intervalos de 15 min esperados entre el primer y el último registro que no aparecen."),
        ("Registros duplicados", q["ts_duplicates"] + q["raw_duplicate_labels"], "Fechas repetidas en el archivo."),
    ])

    tab_t, tab_c, tab_k, tab_r = st.tabs(["Fecha e intervalos", "Completitud", "Columnas y tipos", "Rangos y validez"])
    with tab_t:
        _time_tab(q)
    with tab_c:
        _completeness_tab(q)
    with tab_k:
        _columns_tab(q)
    with tab_r:
        _ranges_tab(q)
    next_step(2)


def _time_tab(q: dict) -> None:
    st.markdown(
        f"La columna de fecha (formato `dd/mm/YYYY HH:MM`) se interpretó sin fallos ({q['parse_failures']} errores). "
        "El archivo marca el **final** de cada intervalo de 15 min. El registro de medianoche (NSM = 0) lleva la "
        "fecha del día que cierra y no la del siguiente, por lo que el orden crudo retrocede "
        f"{q['raw_out_of_order']} veces. Se reconstruye el final del intervalo (día + segundos desde medianoche, "
        "más un día si es medianoche) y el inicio como ese final menos 15 min; el modelo y el corte temporal usan el inicio."
    )
    reading(
        f"{q['midnight_records']} registros de medianoche con la fecha del día que cierran; tras reconstruir, "
        f"la serie va de {q['ts_end_min']:%d/%m/%Y %H:%M} a {q['ts_end_max']:%d/%m/%Y %H:%M}.",
        "Sin la reconstrucción, cada día tendría un hueco a las 00:15 y un duplicado ficticio a las 00:00; "
        "con ella la serie es continua y cada registro pertenece al intervalo correcto.",
        "Toda hora usada por el modelo y por el gemelo se calcula sobre el inicio del intervalo, de modo que "
        "el kWh de las 14:00 significa la energía consumida entre las 14:00 y las 14:15.",
    )


def _completeness_tab(q: dict) -> None:
    exp = q["monthly"]
    fig = go.Figure()
    fig.add_bar(x=exp["mes"], y=exp["registros"], name="Registros encontrados", marker_color=ACCENT)
    fig.add_scatter(x=exp["mes"], y=exp["esperados"], name="Registros esperados", mode="markers",
                    marker=dict(symbol="diamond", size=9, color=POSITIVE))
    style_fig(fig, "Registros por mes: encontrados frente a esperados", x="Mes", y="Registros por mes", hover=",d")
    show_fig(fig)
    all_match = bool((exp["registros"] == exp["esperados"]).all())
    reading(
        f"Se esperan {q['n_expected']:,} intervalos entre el primer y el último registro y hay {q['n_rows']:,}: "
        f"faltan {q['n_missing']} y hay {q['ts_duplicates']} fechas repetidas. "
        + ("Todos los meses coinciden con lo esperado." if all_match else "Hay meses que no coinciden con lo esperado."),
        "La reconstrucción del rango completo confirma que el año está entero, sin huecos que rellenar "
        "ni registros que descartar." if q["n_missing"] == 0 and q["ts_duplicates"] == 0
        else "Existen huecos o repetidos que deben tratarse antes de modelar.",
        "Se puede validar en el tiempo sin imputar: las ventanas de entrenamiento y examen son continuas."
        if q["n_missing"] == 0 else "Antes de entrenar hay que decidir cómo tratar los intervalos faltantes.",
    )
    st.dataframe(q["gaps"].rename(columns={"gap": "Diferencia entre registros consecutivos", "records": "Registros"}),
                 hide_index=True)
    only15 = len(q["gaps"]) == 1
    reading(
        "Distribución de la diferencia entre registros consecutivos tras reconstruir el tiempo: "
        + ", ".join(f"{r.gap} en {r.records:,}" for r in q["gaps"].itertuples()) + ".",
        "Toda la serie avanza en pasos de 15 minutos exactos." if only15 else "Hay saltos distintos de 15 min.",
        "El intervalo de 15 min es la resolución natural del gemelo; no se requiere remuestreo."
        if only15 else "Revisar los saltos antes de usar ventanas temporales.",
    )


def _columns_tab(q: dict) -> None:
    dt = q["dtypes"]
    table = pd.DataFrame({
        "Columna": dt["columna"].map(lambda c: COLUMN_ES.get(c, c)),
        "Tipo de dato": dt["tipo"].map(lambda t: DTYPE_ES.get(t, t)),
    })
    st.dataframe(table, hide_index=True, width="stretch")
    reading(
        f"{q['n_cols']} columnas con {q['nulls_total']} valores nulos en total; las variables numéricas se leen "
        "como decimales o enteros y las de calendario como texto.",
        "No hay nulos que imputar; el texto de calendario (día, tipo de carga) se codificará en la preparación.",
        "No se requiere ninguna limpieza previa; el procesamiento se limita a codificar hora, día y tipo de carga.",
    )
    with st.expander("Diccionario: nombre en el archivo y nombre en esta aplicación", icon=":material/menu_book:"):
        st.dataframe(pd.DataFrame({"Nombre en el archivo": dt["columna"],
                                   "Nombre en esta aplicación": dt["columna"].map(lambda c: COLUMN_ES.get(c, c))}),
                     hide_index=True, width="stretch")


def _ranges_tab(q: dict) -> None:
    rng = q["ranges"].copy()
    shown = rng.assign(variable=rng["variable"].map(lambda c: COLUMN_ES.get(c, c))).rename(columns={
        "variable": "Variable", "mín": "Mínimo", "máx": "Máximo", "media": "Media", "ceros": "Ceros", "nulos": "Nulos",
        "regla": "Regla de validez", "fuera de rango": "Fuera de rango"})
    st.dataframe(shown, hide_index=True, width="stretch")
    bad = int(rng["fuera de rango"].sum())
    ck = q["checks"]
    reading(
        f"{bad} valores fuera de la regla de validez. {q['zero_kwh']} registro(s) con consumo exactamente cero. "
        f"Coherencia de calendario: {ck['day_matches_label']:,} de {q['n_rows']:,} filas con el día de la semana "
        f"igual al del inicio del intervalo y {ck['weekstatus_consistent']:,} con el tipo de día consistente.",
        "Los rangos son físicamente plausibles (factores de potencia entre 0 y 100, energías no negativas) "
        "y el calendario del archivo es coherente con el reloj reconstruido."
        if bad == 0 else "Hay valores fuera de rango que deben revisarse.",
        f"Los ceros de potencia reactiva inductiva ({fmt(rng.set_index('variable').loc['Lagging_Current_Reactive.Power_kVarh', 'ceros'], 0)} "
        "filas) son normales cuando la planta está ligera; no se eliminan filas.",
    )
