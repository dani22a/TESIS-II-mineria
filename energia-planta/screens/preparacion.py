"""Phase 5 - Preparación: hour as sin/cos, day and load type encoding, CO2 out, reproducible pipeline."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import contract, modeling
from lab.config import MODELS, SEED, TARGET
from lab.features import cyclic_hour, feature_names, make_features
from lab.glossary import help_text
from lab.pipeline import split_frames, split_summary
from lab.theme import feature_label, style_fig
from lab.ui import glossary_expander, load_data, next_step, page_header, reading, require_data, show_fig

PURPOSE = ("Convierte hora, día y tipo de carga en las columnas que entiende el modelo y separa el entrenamiento "
           "del examen sin mezclar fechas.")


def _hash(frame: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).to_numpy().tobytes()).hexdigest()[:16]


def render() -> None:
    if require_data(5, PURPOSE) is None:
        return
    _, df = load_data()
    train, exam = split_frames(df)
    sp = split_summary(df)
    names = feature_names()

    page_header(5, PURPOSE, [
        ("Registros de entrenamiento", f"{sp['n_train']:,}", "1 de enero al 30 de septiembre; se usan para ajustar los modelos."),
        ("Registros del examen", f"{sp['n_exam']:,}", "1 de octubre al 31 de diciembre; no se tocan al ajustar."),
        ("Columnas del modelo", len(names), "2 de hora, 7 de día de la semana y 3 de tipo de carga."),
        ("Semilla fija", SEED, "Número que hace repetible cualquier paso con azar."),
    ])

    tab_c, tab_h, tab_v, tab_r = st.tabs(["Corte temporal", "La hora como círculo", "Variables y pipelines", "Reproducibilidad"])
    with tab_c:
        _split_tab(sp)
    with tab_h:
        _hour_tab()
    with tab_v:
        _features_tab(train, names)
    with tab_r:
        _repro_tab(train, exam)
    glossary_expander(["TimeSeriesSplit"], "Glosario: validación temporal")
    next_step(5)


def _split_tab(sp: dict) -> None:
    st.dataframe(pd.DataFrame([
        {"Conjunto": "Entrenamiento (con TimeSeriesSplit interno)", "Desde": sp["train_start"], "Hasta": sp["train_end"], "Registros": sp["n_train"]},
        {"Conjunto": "Examen (último trimestre, no se toca al ajustar)", "Desde": sp["exam_start"], "Hasta": sp["exam_end"], "Registros": sp["n_exam"]},
    ]), hide_index=True, width="stretch")
    reading(
        f"{sp['n_train']:,} registros para entrenar (1 ene a 30 sep) y {sp['n_exam']:,} para el examen (1 oct a 31 dic). "
        "El corte usa el inicio del intervalo: el registro del 1 ene 2019 00:00 empieza el 31 dic 23:45 y cae en el examen.",
        "El examen es el futuro respecto del entrenamiento: simula cómo trabajaría el modelo en la planta al llegar "
        "el último trimestre, sin que ningún dato de octubre a diciembre influya en el ajuste.",
        "El error medido en el examen es la mejor estimación honesta del error que verá el gemelo en operación.",
    )


def _hour_tab() -> None:
    slots = np.arange(0, 24, 0.25)
    s, c = cyclic_hour(slots)
    fig = go.Figure(go.Scatter(
        x=c, y=s, mode="markers+text", text=[f"{int(h):02d}h" if h == int(h) and int(h) % 3 == 0 else "" for h in slots],
        textposition="top center", marker=dict(size=7, color=slots, colorscale="Viridis", showscale=True,
                                               colorbar=dict(title="Hora del día")),
        customdata=slots, hovertemplate="Hora %{customdata:.2f}<br>Coseno %{x:.2f}, seno %{y:.2f}<extra></extra>"))
    style_fig(fig, "Las 96 posiciones del día forman un círculo", x="Hora (coseno)", y="Hora (seno)", height=460, legend=False)
    fig.update_layout(yaxis_scaleanchor="x", margin=dict(t=64))
    show_fig(fig)
    end = np.hypot(*(np.array(cyclic_hour(23.75)) - np.array(cyclic_hour(0.0))))
    noon = np.hypot(*(np.array(cyclic_hour(12.0)) - np.array(cyclic_hour(0.0))))
    reading(
        f"Las 96 posiciones del día forman un círculo. La distancia entre las 23:45 y las 00:00 es {end:.2f}, mientras que "
        f"entre las 00:00 y las 12:00 es {noon:.2f}; con la hora cruda esas dos primeras estarían a 23.75 unidades.",
        "El reloj es circular: la medianoche continúa en la madrugada. Codificarlo con seno y coseno (periodo 24 h) "
        "conserva esa cercanía, algo que un número de 0 a 23 rompe.",
        "El gemelo solo entrega la hora del reloj de simulación; el modelo la convierte con estas dos fórmulas fijas.",
    )


def _features_tab(train: pd.DataFrame, names: list[str]) -> None:
    st.dataframe(pd.DataFrame({
        "Columna del modelo": [feature_label(n) for n in names],
        "Variable de origen": ["Hora del día"] * 2 + ["Día de la semana"] * 7 + ["Tipo de carga"] * 3,
        "Codificación": ["Seno", "Coseno"] + ["Una columna por día (0 o 1)"] * 7 + ["Una columna por tipo (0 o 1)"] * 3,
    }), hide_index=True, width="stretch")
    reading(
        f"El modelo recibe {len(names)} columnas: 2 de hora, 7 de día y 3 de tipo de carga. CO2, reactiva, factor de potencia, "
        "NSM y WeekStatus no participan.",
        "Un único preprocesamiento (ColumnTransformer con categorías fijas) sirve a los tres modelos y coincide con el "
        "contrato que lee el gemelo. Elastic Net escala dentro de su pipeline; los árboles no lo necesitan.",
        "Cualquier señal nueva del gemelo debe encajar en estas columnas; si se añade una variable, hay que reentrenar.",
    )
    with st.expander("Detalle técnico: pipeline de cada modelo", icon=":material/code:"):
        for name in MODELS:
            st.markdown(f"**{name}**")
            st.code(str(modeling.build_pipeline(name)), language="text")
        st.caption(contract.PREPROCESSING["elastic_net"] + " | " + contract.PREPROCESSING["trees"])


def _repro_tab(train: pd.DataFrame, exam: pd.DataFrame) -> None:
    X_train = make_features(train)
    pipe_a = modeling.build_pipeline("Elastic Net")
    pipe_b = modeling.build_pipeline("Elastic Net")
    pipe_a.fit(X_train, train[TARGET])
    pipe_b.fit(X_train, train[TARGET])
    same_pred = bool(np.array_equal(pipe_a.predict(make_features(exam)), pipe_b.predict(make_features(exam))))
    same_feat = _hash(X_train) == _hash(make_features(train))
    st.dataframe(pd.DataFrame([
        {"Verificación": "Semilla global", "Resultado": str(SEED)},
        {"Verificación": "Las columnas del modelo son idénticas al reconstruirlas", "Resultado": "✅ Sí" if same_feat else "⚠️ No"},
        {"Verificación": "Dos ajustes con la misma semilla dan igual predicción", "Resultado": "✅ Sí" if same_pred else "⚠️ No"},
        {"Verificación": "Huella de las columnas de entrenamiento", "Resultado": _hash(X_train)},
    ]), hide_index=True, width="stretch")
    reading(
        f"Semilla {SEED}; reconstrucción de las columnas idéntica: {'sí' if same_feat else 'no'}; dos ajustes de Elastic Net "
        f"con las mismas entradas dan la misma predicción: {'sí' if same_pred else 'no'}.",
        "La preparación es determinista: mismos datos y semilla producen el mismo resultado, requisito para comparar modelos "
        "y para poder repetir el entrenamiento.",
        "Cuando se reentrene con datos nuevos, una diferencia de error se deberá a los datos y no al azar del ajuste.",
    )
