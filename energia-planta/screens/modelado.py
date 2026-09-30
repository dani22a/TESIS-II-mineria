"""Phase 6 - Modelado: hyperparameter search with temporal validation and frozen hyperparameters."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import modeling, pipeline
from lab.config import MODELS
from lab.ui import not_trained_message, read_json, reading


def _train_button() -> None:
    if st.button("Entrenar / Re-entrenar (búsqueda de hiperparámetros)", key="btn_modelado"):
        bar = st.progress(0.0)
        with st.spinner("Buscando hiperparámetros con validación temporal (1 a 2 minutos)..."):
            pipeline.run_modeling(progress=lambda msg, frac: bar.progress(min(frac, 1.0), text=msg))
        st.success("Hiperparámetros congelados y guardados en artefactos/.")
        st.rerun()


def render() -> None:
    st.header("6. Modelado")
    st.markdown(
        "Se busca con `RandomizedSearchCV` (semilla 42, métrica MAE) sobre el período de entrenamiento, "
        "usando `TimeSeriesSplit` para que cada validación quede siempre después de su entrenamiento. "
        "Al terminar, los hiperparámetros se congelan y no se vuelven a tocar."
    )
    frozen = read_json(pipeline.FROZEN)

    st.subheader("Espacios de búsqueda")
    rows = [{"modelo": m, "hiperparámetro": k, "distribución": v[1]} for m, sp in modeling.SEARCH_SPACES.items() for k, v in sp.items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    reading(
        f"Elastic Net busca {len(modeling.SEARCH_SPACES['Elastic Net'])} hiperparámetros, Random Forest "
        f"{len(modeling.SEARCH_SPACES['Random Forest'])} y XGBoost {len(modeling.SEARCH_SPACES['XGBoost'])}; "
        "cada uno con una distribución acotada y un número fijo de candidatos aleatorios.",
        "Los rangos limitan la complejidad (profundidad, hojas mínimas, regularización) para que el modelo no memorice "
        "los turnos de un solo trimestre.",
        "Un espacio pequeño y acotado mantiene el tiempo de reentrenamiento bajo (del orden de un minuto), viable "
        "para repetirlo cuando cambie la operación de la planta.",
    )

    if frozen is None:
        not_trained_message("La búsqueda de hiperparámetros")
        _train_button()
        return

    st.subheader("Validación temporal dentro del entrenamiento")
    folds = frozen["cv"]["folds"]
    fig = go.Figure()
    for f in folds:
        fig.add_trace(go.Bar(y=[f"Pliegue {f['fold']}"], x=[pd.Timestamp(f["train_end"]).value - pd.Timestamp(f["train_start"]).value],
                             base=[pd.Timestamp(f["train_start"])], orientation="h", marker_color="#9db7d5", showlegend=False,
                             hovertext=f"Entrena: {f['train_start'][:10]} a {f['train_end'][:10]} ({f['n_train']:,})"))
        fig.add_trace(go.Bar(y=[f"Pliegue {f['fold']}"], x=[pd.Timestamp(f["val_end"]).value - pd.Timestamp(f["val_start"]).value],
                             base=[pd.Timestamp(f["val_start"])], orientation="h", marker_color="#f2a541", showlegend=False,
                             hovertext=f"Valida: {f['val_start'][:10]} a {f['val_end'][:10]} ({f['n_val']:,})"))
    sp = frozen["split"]
    fig.add_vline(x=pd.Timestamp(sp["exam_start"]).timestamp() * 1000, line_dash="dash", line_color="#d64550",
                  annotation_text="Examen (intocable)")
    fig.update_xaxes(type="date")
    fig.update_traces(width=0.6)
    fig.update_layout(template="plotly_white", barmode="overlay", height=340, yaxis_autorange="reversed")
    st.plotly_chart(fig, width="stretch")
    reading(
        f"{len(folds)} pliegues: azul es el entrenamiento (crece de {folds[0]['n_train']:,} a {folds[-1]['n_train']:,} registros) y naranja la "
        f"validación posterior de unos {folds[0]['n_val']:,} registros. El examen empieza el {sp['exam_start'][:10]} y queda fuera.",
        "Cada pliegue evalúa hacia adelante, como operará el modelo en la planta; nunca se valida con datos "
        "anteriores al entrenamiento ni con datos del examen.",
        "El error de validación cruzada es un estimador honesto para elegir hiperparámetros sin usar el trimestre de examen.",
    )

    st.subheader("Hiperparámetros congelados")
    rows = []
    for m in MODELS:
        info = frozen["models"][m]
        rows.append({"modelo": m, "MAE de validación (kWh)": round(info["cv_mae"], 3), "desviación entre pliegues": round(info["cv_mae_std"], 3),
                     "candidatos": info["n_iter"], "segundos": info["seconds"],
                     "hiperparámetros": ", ".join(f"{k} = {v:.4g}" if isinstance(v, float) else f"{k} = {v}" for k, v in info["params"].items())})
    tbl = pd.DataFrame(rows)
    st.dataframe(tbl, hide_index=True, width="stretch")
    ranked = tbl.sort_values("MAE de validación (kWh)")
    best, worst = ranked.iloc[0], ranked.iloc[-1]
    reading(
        f"MAE de validación: " + ", ".join(f"{r['modelo']} {r['MAE de validación (kWh)']:.2f}" for _, r in ranked.iterrows())
        + f" kWh. El menor es {best['modelo']}; el mayor {worst['modelo']}.",
        f"{worst['modelo']} queda {worst['MAE de validación (kWh)'] - best['MAE de validación (kWh)']:.1f} kWh por encima de {best['modelo']}"
        + (": con solo hora, día y carga, los modelos que capturan interacciones (turnos por carga) superan al lineal."
           if worst["modelo"] == "Elastic Net" else "."),
        "Estos valores quedan congelados; el examen decidirá el modelo que se exporta, no la validación cruzada.",
    )

    st.subheader("Error por pliegue del mejor candidato")
    fig2 = go.Figure()
    for m in MODELS:
        fig2.add_trace(go.Scatter(x=[f"Pliegue {i + 1}" for i in range(len(folds))], y=frozen["models"][m]["cv_mae_folds"],
                                  mode="lines+markers", name=m))
    fig2.update_layout(template="plotly_white", height=340, yaxis_title="MAE (kWh)")
    st.plotly_chart(fig2, width="stretch")
    spread = {m: max(frozen["models"][m]["cv_mae_folds"]) - min(frozen["models"][m]["cv_mae_folds"]) for m in MODELS}
    widest = max(spread, key=spread.get)
    reading(
        "MAE por pliegue: " + "; ".join(f"{m} entre {min(frozen['models'][m]['cv_mae_folds']):.1f} y {max(frozen['models'][m]['cv_mae_folds']):.1f}" for m in MODELS) + " kWh.",
        f"El error cambia de un período a otro ({widest} varía {spread[widest]:.1f} kWh entre pliegues): el nivel de la planta no es estable en el tiempo, "
        "lo que confirma que la validación debe ser temporal.",
        "Al leer el examen, se espera una variación similar; no conviene comparar modelos por una sola cifra.",
    )

    cand = read_json(pipeline.SEARCH)
    if cand:
        with st.expander("Mejores 10 candidatos por modelo"):
            for m in MODELS:
                st.markdown(f"**{m}**")
                st.dataframe(pd.DataFrame(cand[m]), hide_index=True, width="stretch")
    _train_button()
