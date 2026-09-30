"""Phase 6 - Modelado: hyperparameter search with temporal validation and frozen hyperparameters."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import modeling, pipeline
from lab.config import MODEL_COLORS, MODELS
from lab.glossary import help_text
from lab.theme import NEUTRAL, POSITIVE, style_fig
from lab.ui import glossary_expander, next_step, not_trained_message, page_header, read_json, reading, show_fig

PURPOSE = ("Busca los mejores ajustes de cada modelo probando candidatos al azar y validando siempre hacia adelante "
           "en el tiempo; al terminar, los ajustes quedan congelados.")


def _train_button() -> None:
    if st.button("Entrenar / Re-entrenar (búsqueda de hiperparámetros)", key="btn_modelado", type="primary"):
        bar = st.progress(0.0)
        with st.spinner("Buscando hiperparámetros con validación temporal (1 a 2 minutos)..."):
            pipeline.run_modeling(progress=lambda msg, frac: bar.progress(min(frac, 1.0), text=msg))
        st.success("Hiperparámetros congelados y guardados en artefactos/.")
        st.rerun()


def render() -> None:
    frozen = read_json(pipeline.FROZEN)
    if frozen is None:
        kpis = [("Modelos comparados", len(MODELS), "Elastic Net, Random Forest y XGBoost."),
                ("Métrica de selección", "MAE (kWh)", help_text("MAE")),
                ("Pliegues de validación", "Sin calcular", "Se calculan al entrenar."),
                ("Mejor MAE de validación", "Sin calcular", "Se calcula al entrenar.")]
    else:
        info = frozen["models"]
        best = min(MODELS, key=lambda m: info[m]["cv_mae"])
        kpis = [("Modelos comparados", len(MODELS), "Elastic Net, Random Forest y XGBoost."),
                ("Pliegues de validación", len(frozen["cv"]["folds"]), help_text("TimeSeriesSplit")),
                ("Mejor MAE de validación", f"{info[best]['cv_mae']:.2f} kWh", f"{best}. " + help_text("MAE")),
                ("Tiempo de búsqueda", f"{sum(info[m]['seconds'] for m in MODELS):.0f} s", "Suma de los tres modelos.")]
    page_header(6, PURPOSE, kpis)

    tab_q, tab_v, tab_r, tab_c = st.tabs(["Qué se busca", "Validación temporal", "Resultados", "Mejores candidatos"])
    with tab_q:
        _search_tab()
    if frozen is None:
        for tab in (tab_v, tab_r, tab_c):
            with tab:
                not_trained_message("La búsqueda de hiperparámetros", button=tab is tab_r)
        with tab_r:
            _train_button()
    else:
        with tab_v:
            _validation_tab(frozen)
        with tab_r:
            _results_tab(frozen)
            _train_button()
        with tab_c:
            _candidates_tab()
    glossary_expander(["MAE", "TimeSeriesSplit"], "Glosario: validación y error")
    next_step(6)


def _search_tab() -> None:
    st.markdown(
        "Se busca con `RandomizedSearchCV` (semilla 42, métrica MAE) sobre el período de entrenamiento, "
        "usando validación temporal (`TimeSeriesSplit`) para que cada validación quede siempre después de su entrenamiento. "
        "Al terminar, los hiperparámetros se congelan y no se vuelven a tocar."
    )
    rows = [{"Modelo": m, "Hiperparámetro": k, "Distribución de búsqueda": v[1]}
            for m, sp in modeling.SEARCH_SPACES.items() for k, v in sp.items()]
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


def _validation_tab(frozen: dict) -> None:
    folds = frozen["cv"]["folds"]
    fig = go.Figure()
    for i, f in enumerate(folds):
        fig.add_trace(go.Bar(y=[f"Pliegue {f['fold']}"], x=[pd.Timestamp(f["train_end"]).value - pd.Timestamp(f["train_start"]).value],
                             base=[pd.Timestamp(f["train_start"])], orientation="h", marker_color=NEUTRAL,
                             name="Entrenamiento", legendgroup="train", showlegend=i == 0,
                             hovertext=f"Entrena: {f['train_start'][:10]} a {f['train_end'][:10]} ({f['n_train']:,} registros)",
                             hoverinfo="text"))
        fig.add_trace(go.Bar(y=[f"Pliegue {f['fold']}"], x=[pd.Timestamp(f["val_end"]).value - pd.Timestamp(f["val_start"]).value],
                             base=[pd.Timestamp(f["val_start"])], orientation="h", marker_color=MODEL_COLORS["XGBoost"],
                             name="Validación", legendgroup="val", showlegend=i == 0,
                             hovertext=f"Valida: {f['val_start'][:10]} a {f['val_end'][:10]} ({f['n_val']:,} registros)",
                             hoverinfo="text"))
    sp = frozen["split"]
    fig.add_vline(x=pd.Timestamp(sp["exam_start"]).timestamp() * 1000, line_dash="dash", line_color=POSITIVE,
                  annotation_text="Inicio del examen (intocable)")
    fig.update_xaxes(type="date")
    fig.update_traces(width=0.6)
    style_fig(fig, "Cada pliegue entrena con el pasado y valida con el período siguiente", x="Fecha", y=None, height=360)
    fig.update_layout(barmode="overlay", yaxis_autorange="reversed")
    show_fig(fig)
    reading(
        f"{len(folds)} pliegues: gris es el entrenamiento (crece de {folds[0]['n_train']:,} a {folds[-1]['n_train']:,} registros) y azul la "
        f"validación posterior de unos {folds[0]['n_val']:,} registros. El examen empieza el {sp['exam_start'][:10]} y queda fuera.",
        "Cada pliegue evalúa hacia adelante, como operará el modelo en la planta; nunca se valida con datos "
        "anteriores al entrenamiento ni con datos del examen.",
        "El error de validación cruzada es un estimador honesto para elegir hiperparámetros sin usar el trimestre de examen.",
    )


def _results_tab(frozen: dict) -> None:
    folds = frozen["cv"]["folds"]
    rows = []
    for m in MODELS:
        info = frozen["models"][m]
        rows.append({"Modelo": m, "MAE de validación (kWh)": round(info["cv_mae"], 3), "Desviación entre pliegues (kWh)": round(info["cv_mae_std"], 3),
                     "Candidatos probados": info["n_iter"], "Segundos": info["seconds"],
                     "Hiperparámetros elegidos": ", ".join(f"{k} = {v:.4g}" if isinstance(v, float) else f"{k} = {v}" for k, v in info["params"].items())})
    tbl = pd.DataFrame(rows)
    st.dataframe(tbl, hide_index=True, width="stretch")
    ranked = tbl.sort_values("MAE de validación (kWh)")
    best, worst = ranked.iloc[0], ranked.iloc[-1]
    reading(
        "MAE de validación: " + ", ".join(f"{r['Modelo']} {r['MAE de validación (kWh)']:.2f}" for _, r in ranked.iterrows())
        + f" kWh. El menor es {best['Modelo']}; el mayor {worst['Modelo']}.",
        f"{worst['Modelo']} queda {worst['MAE de validación (kWh)'] - best['MAE de validación (kWh)']:.1f} kWh por encima de {best['Modelo']}"
        + (": con solo hora, día y carga, los modelos que capturan interacciones (turnos por carga) superan al lineal."
           if worst["Modelo"] == "Elastic Net" else "."),
        "Estos valores quedan congelados; el examen decidirá el modelo que se exporta, no la validación cruzada.",
    )

    fig2 = go.Figure()
    for m in MODELS:
        fig2.add_trace(go.Scatter(x=[f"Pliegue {i + 1}" for i in range(len(folds))], y=frozen["models"][m]["cv_mae_folds"],
                                  mode="lines+markers", name=m, line=dict(color=MODEL_COLORS[m])))
    style_fig(fig2, "Error de validación (MAE) de cada modelo en cada pliegue", x="Pliegue de validación", y="MAE (kWh)", height=360)
    show_fig(fig2)
    spread = {m: max(frozen["models"][m]["cv_mae_folds"]) - min(frozen["models"][m]["cv_mae_folds"]) for m in MODELS}
    widest = max(spread, key=spread.get)
    reading(
        "MAE por pliegue: " + "; ".join(f"{m} entre {min(frozen['models'][m]['cv_mae_folds']):.1f} y {max(frozen['models'][m]['cv_mae_folds']):.1f}" for m in MODELS) + " kWh.",
        f"El error cambia de un período a otro ({widest} varía {spread[widest]:.1f} kWh entre pliegues): el nivel de la planta no es estable en el tiempo, "
        "lo que confirma que la validación debe ser temporal.",
        "Al leer el examen, se espera una variación similar; no conviene comparar modelos por una sola cifra.",
    )


def _candidates_tab() -> None:
    cand = read_json(pipeline.SEARCH)
    if not cand:
        st.info("Aún no hay lista de candidatos guardada.")
        return
    st.caption("Los 10 mejores candidatos de cada modelo, ordenados por MAE de validación.")
    for m in MODELS:
        st.markdown(f"**{m}**")
        st.dataframe(pd.DataFrame(cand[m]), hide_index=True, width="stretch")
