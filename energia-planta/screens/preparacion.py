"""Phase 5 - Preparación: hour as sin/cos, day and load type encoding, CO2 out, reproducible pipeline."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import contract, modeling
from lab.config import SEED, TARGET
from lab.features import cyclic_hour, feature_names, make_features
from lab.pipeline import split_frames, split_summary
from lab.ui import load_data, reading, require_data


def _hash(frame: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).to_numpy().tobytes()).hexdigest()[:16]


def render() -> None:
    st.header("5. Preparación")
    if require_data() is None:
        return
    _, df = load_data()
    train, exam = split_frames(df)
    sp = split_summary(df)

    st.subheader("Corte temporal")
    st.dataframe(pd.DataFrame([
        {"conjunto": "Entrenamiento (con TimeSeriesSplit interno)", "desde": sp["train_start"], "hasta": sp["train_end"], "registros": sp["n_train"]},
        {"conjunto": "Examen (último trimestre, no se toca al ajustar)", "desde": sp["exam_start"], "hasta": sp["exam_end"], "registros": sp["n_exam"]},
    ]), hide_index=True, width="stretch")
    reading(
        f"{sp['n_train']:,} registros para entrenar (1 ene a 30 sep) y {sp['n_exam']:,} para el examen (1 oct a 31 dic). "
        "El corte usa el inicio del intervalo: el registro del 1 ene 2019 00:00 empieza el 31 dic 23:45 y cae en el examen.",
        "El examen es el futuro respecto del entrenamiento: simula cómo trabajaría el modelo en la planta al llegar "
        "el último trimestre, sin que ningún dato de octubre a diciembre influya en el ajuste.",
        "El error medido en el examen es la mejor estimación honesta del error que verá el gemelo en operación.",
    )

    st.subheader("La hora como seno y coseno")
    slots = np.arange(0, 24, 0.25)
    s, c = cyclic_hour(slots)
    fig = go.Figure(go.Scatter(x=c, y=s, mode="markers+text", text=[f"{int(h):02d}h" if h == int(h) and int(h) % 3 == 0 else "" for h in slots],
                               textposition="top center", marker=dict(size=6, color=slots, colorscale="Turbo", showscale=True,
                                                                     colorbar=dict(title="hora"))))
    fig.update_layout(template="plotly_white", height=420, xaxis_title="hour_cos", yaxis_title="hour_sin",
                      yaxis_scaleanchor="x")
    st.plotly_chart(fig, width="stretch")
    end = np.hypot(*(np.array(cyclic_hour(23.75)) - np.array(cyclic_hour(0.0))))
    noon = np.hypot(*(np.array(cyclic_hour(12.0)) - np.array(cyclic_hour(0.0))))
    reading(
        f"Las 96 posiciones del día forman un círculo. La distancia entre las 23:45 y las 00:00 es {end:.2f}, mientras que "
        f"entre las 00:00 y las 12:00 es {noon:.2f}; con la hora cruda esas dos primeras estarían a 23.75 unidades.",
        "El reloj es circular: la medianoche continúa en la madrugada. Codificarlo con seno y coseno (periodo 24 h) "
        "conserva esa cercanía, algo que un número de 0 a 23 rompe.",
        "El gemelo solo entrega la hora del reloj de simulación; el modelo la convierte con estas dos fórmulas fijas.",
    )

    st.subheader("Variables del modelo y pipelines")
    names = feature_names()
    X_train = make_features(train)
    st.dataframe(pd.DataFrame({
        "columna del modelo": names,
        "origen": ["hour (seno)", "hour (coseno)"] + ["day (one-hot)"] * 7 + ["load_type (one-hot)"] * 3,
    }), hide_index=True)
    reading(
        f"El modelo recibe {len(names)} columnas: 2 de hora, 7 de día y 3 de tipo de carga. CO2, reactiva, factor de potencia, "
        "NSM y WeekStatus no participan.",
        "Un único preprocesamiento (ColumnTransformer con categorías fijas) sirve a los tres modelos y coincide con el "
        "contrato que lee el gemelo. Elastic Net escala dentro de su pipeline; los árboles no lo necesitan.",
        "Cualquier señal nueva del gemelo debe encajar en estas columnas; si se añade una variable, hay que reentrenar.",
    )
    for name in ("Elastic Net", "Random Forest", "XGBoost"):
        with st.expander(f"Pipeline de {name}"):
            st.code(str(modeling.build_pipeline(name)), language="text")
    st.caption(contract.PREPROCESSING["elastic_net"] + " | " + contract.PREPROCESSING["trees"])

    st.subheader("Reproducibilidad")
    pipe_a = modeling.build_pipeline("Elastic Net")
    pipe_b = modeling.build_pipeline("Elastic Net")
    pipe_a.fit(X_train, train[TARGET])
    pipe_b.fit(X_train, train[TARGET])
    same_pred = bool(np.array_equal(pipe_a.predict(make_features(exam)), pipe_b.predict(make_features(exam))))
    same_feat = _hash(X_train) == _hash(make_features(train))
    st.dataframe(pd.DataFrame([
        {"verificación": "Semilla global", "resultado": str(SEED)},
        {"verificación": "Features idénticas al reconstruirlas", "resultado": "Sí" if same_feat else "No"},
        {"verificación": "Dos ajustes con la misma semilla dan igual predicción", "resultado": "Sí" if same_pred else "No"},
        {"verificación": "Huella de las features de entrenamiento", "resultado": _hash(X_train)},
    ]), hide_index=True)
    reading(
        f"Semilla {SEED}; reconstrucción de features idéntica: {'sí' if same_feat else 'no'}; dos ajustes de Elastic Net "
        f"con las mismas entradas dan la misma predicción: {'sí' if same_pred else 'no'}.",
        "La preparación es determinista: mismos datos y semilla producen el mismo resultado, requisito para comparar modelos "
        "y para poder repetir el entrenamiento.",
        "Cuando se reentrene con datos nuevos, una diferencia de error se deberá a los datos y no al azar del ajuste.",
    )
