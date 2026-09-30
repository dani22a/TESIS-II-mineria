"""Phase 4 - Pruebas: statistical tests and the decision on which variables enter."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import stats_tests as T
from lab.config import LOAD_ES, LOAD_TYPES
from lab.ui import load_data, read_json, reading, require_data


@st.cache_data(show_spinner="Ejecutando pruebas estadísticas...")
def _tests() -> dict:
    _, df = load_data()
    return T.run_data_tests(df)


def render() -> None:
    st.header("4. Pruebas")
    if require_data() is None:
        return
    t = _tests()
    kl, kh, mw = t["kruskal_load"], t["kruskal_hour"], t["mann_whitney"]

    st.subheader("Tabla de pruebas")
    st.dataframe(T.test_table(t), hide_index=True, width="stretch")
    reading(
        f"Todas las pruebas de diferencia (Kruskal-Wallis y Mann-Whitney) dan p menor a 0.001 con 35,040 registros; "
        f"el tipo de carga explica una parte grande de la variación (efecto {kl['eps2']:.2f}) y la hora también ({kh['eps2']:.2f}).",
        "Con tantos datos casi cualquier diferencia sale significativa, por eso importa el tamaño del efecto y no solo el p: "
        "hora, carga y día separan el consumo de forma sustantiva, mientras que CO2 y kWh son casi la misma variable.",
        "Las tres variables del gemelo (hora, día, carga) están justificadas como entradas; las demás columnas se "
        "descartan por no poder producirse en el gemelo o por ser redundantes.",
    )

    st.subheader("Kruskal-Wallis y Dunn: consumo por tipo de carga")
    dunn = kl["dunn"].rename(index=LOAD_ES, columns=LOAD_ES)
    fig = go.Figure(go.Heatmap(z=-np.log10(np.clip(dunn.to_numpy(dtype=float), 1e-300, 1.0)),
                               x=list(dunn.columns), y=list(dunn.index), colorscale="Blues",
                               text=[[("-" if i == j else "< 0.001" if v < 0.001 else f"{v:.3f}")
                                      for j, v in enumerate(row)] for i, row in enumerate(dunn.values)],
                               texttemplate="%{text}", colorbar=dict(title="-log10(p)")))
    fig.update_layout(template="plotly_white", height=320)
    st.plotly_chart(fig, width="stretch")
    med = kl["medians"]
    all_sig = bool(((dunn.values < 0.001) | (dunn.values == 1.0)).all())
    reading(
        f"H = {kl['H']:,.0f}, p menor a 0.001. Medianas: ligera {med['Light_Load']:.1f}, media {med['Medium_Load']:.1f} "
        f"y máxima {med['Maximum_Load']:.1f} kWh. En Dunn con Bonferroni "
        + ("los tres pares difieren con p menor a 0.001." if all_sig else "no todos los pares difieren."),
        "Los tres regímenes de carga son estadísticamente distintos entre sí, sin solaparse en la mediana.",
        "Se conserva el tipo de carga completo (tres niveles) y no se fusionan categorías.",
    )

    st.subheader("Mann-Whitney: día laborable frente a fin de semana")
    st.dataframe(pd.DataFrame([{
        "grupo": "Lunes a viernes", "registros": mw["n_weekday"], "mediana kWh": mw["median_weekday"], "media kWh": mw["mean_weekday"]},
        {"grupo": "Sábado y domingo", "registros": mw["n_weekend"], "mediana kWh": mw["median_weekend"], "media kWh": mw["mean_weekend"]}]),
        hide_index=True)
    reading(
        f"U = {mw['U']:,.0f}, p menor a 0.001; medias de {mw['mean_weekday']:.1f} kWh entre semana y {mw['mean_weekend']:.1f} kWh "
        f"en fin de semana; correlación biserial de rangos {mw['rank_biserial']:.2f}.",
        f"El consumo medio del fin de semana equivale a {mw['mean_weekend'] / mw['mean_weekday']:.0%} del de un día laborable.",
        "El día de la semana entra al modelo; el gemelo debe esperar demanda baja sábado y domingo.",
    )

    st.subheader("VIF: por qué el CO2 no entra")
    vif = t["vif"]
    st.dataframe(vif.round(1), hide_index=True)
    v = vif.set_index("variable")
    reading(
        f"Con el CO2 en el conjunto, el VIF del CO2 es {v.loc['CO2(tCO2)', 'VIF con CO2']:.1f} y el del consumo "
        f"{v.loc['Usage_kWh', 'VIF con CO2']:.1f}; sin CO2 el del consumo baja a {v.loc['Usage_kWh', 'VIF sin CO2']:.1f}.",
        "Un VIF por encima de 10 indica que la variable se explica casi por completo con las demás: el CO2 y el "
        "consumo son redundantes entre sí.",
        "El CO2 queda fuera del modelo y se calcula después desde los kWh, para no inflar la precisión con una copia del objetivo.",
    )

    st.subheader("KPSS: por qué se valida en el tiempo")
    k = t["kpss"]
    st.dataframe(k.round(3), hide_index=True)
    rej = bool((k["p (acotado a 0.01-0.10)"] < 0.05).all())
    reading(
        f"El estadístico KPSS es {k.iloc[0]['estadístico']:.2f} (nivel) y {k.iloc[1]['estadístico']:.2f} (tendencia), con p en el "
        f"límite inferior de la tabla (0.01). La autocorrelación a 15 min es {t['acf']['lag1']:.2f} y a 24 h {t['acf']['lag96']:.2f}.",
        ("Se rechaza que la serie sea estacionaria: su nivel cambia con el tiempo, y las observaciones vecinas se parecen mucho."
         if rej else "No se rechaza la estacionariedad en todas las variantes; aun así la autocorrelación es alta."),
        "Se valida hacia adelante (entrenar en el pasado, examinar en el futuro) con TimeSeriesSplit; una partición aleatoria "
        "mezclaría vecinos casi idénticos y daría un error optimista.",
    )

    st.subheader("Decisión sobre las variables")
    st.dataframe(T.variable_decisions(t), hide_index=True, width="stretch")
    reading(
        "Entran hora, día y tipo de carga; quedan fuera reactiva, factor de potencia, NSM, WeekStatus y CO2.",
        "La decisión combina evidencia estadística (efecto grande de hora, día y carga) con la restricción de negocio: "
        "solo se usa lo que el gemelo puede producir.",
        "El siguiente paso, Preparación, construye un pipeline reproducible con estas tres variables y la semilla 42.",
    )

    _model_tests()


def _model_tests() -> None:
    """Friedman/Nemenyi and Diebold-Mariano results between models (computed at training time)."""
    st.subheader("Pruebas entre modelos")
    res = read_json("pruebas_modelos.json")
    if res is None:
        st.info("Estas pruebas se calculan al entrenar los modelos: ejecute `python train.py` o el botón de la pantalla Evaluación.")
        return
    fn, dm = res["friedman_nemenyi"], res["diebold_mariano"]
    rows = [{"prueba": "Friedman sobre el MAE semanal del examen", "estadístico": f"chi² = {fn['chi2']:.2f}",
             "p": "< 0.001" if fn["p"] < 0.001 else f"{fn['p']:.3f}",
             "lectura": "Rangos medios: " + ", ".join(f"{k} {v:.2f}" for k, v in fn["mean_ranks"].items())}]
    models = list(fn["mean_ranks"])
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            p = fn["nemenyi"][a][b]
            rows.append({"prueba": f"Nemenyi: {a} vs {b}", "estadístico": "-", "p": "< 0.001" if p < 0.001 else f"{p:.3f}",
                         "lectura": "Difieren" if p < 0.05 else "No se distinguen"})
    for r in dm:
        rows.append({"prueba": f"Diebold-Mariano (diciembre): {r['model_a']} vs {r['model_b']}", "estadístico": f"DM = {r['stat']:.2f}",
                     "p": "< 0.001" if r["p"] < 0.001 else f"{r['p']:.3f}",
                     "lectura": f"Diferencia media de error {r['mean_diff']:+.2f} kWh (negativa: {r['model_a']} mejor)"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    reading(
        f"Friedman con {fn['n_windows']} semanas: p {'menor a 0.001' if fn['p'] < 0.001 else round(fn['p'], 3)}. "
        + " ".join(f"XGBoost frente a {r['model_b']}: p {r['p']:.3g}." for r in dm),
        "Friedman y Nemenyi ordenan los modelos por su error semanal; Diebold-Mariano contrasta las predicciones de diciembre con una "
        "varianza robusta a la autocorrelación.",
        "El detalle y las figuras están en Evaluación; aquí queda el registro de que la elección del modelo se apoya en pruebas y no solo en un promedio.",
    )
