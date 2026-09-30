"""Phase 4 - Pruebas: statistical tests and the decision on which variables enter."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import stats_tests as T
from lab.config import LOAD_SHORT
from lab.glossary import help_text
from lab.theme import COLUMN_SHORT, style_fig
from lab.ui import (fmt_p, glossary_expander, load_data, next_step, not_trained_message, page_header, read_json,
                    reading, require_data, show_fig)

PURPOSE = ("Comprueba con pruebas estadísticas si hora, día y tipo de carga cambian el consumo, "
           "y decide qué variables entran al modelo y cuáles no.")


@st.cache_data(show_spinner="Ejecutando pruebas estadísticas...")
def _tests() -> dict:
    _, df = load_data()
    return T.run_data_tests(df)


def _style_decision(df: pd.DataFrame):
    def color(v: str) -> str:
        if v.startswith("✅"):
            return "background-color: #E3F3E8; color: #14532D; font-weight: 600"
        return "background-color: #FBE9E7; color: #7F1D1D; font-weight: 600"

    return df.style.map(color, subset=["Decisión"])


def render() -> None:
    if require_data(4, PURPOSE) is None:
        return
    _, df = load_data()
    t = _tests()
    kl, kh, mw = t["kruskal_load"], t["kruskal_hour"], t["mann_whitney"]
    decisions = T.variable_decisions(t)
    enter = int(decisions["decisión"].str.startswith("✅").sum())
    vif = t["vif"].set_index("variable")

    page_header(4, PURPOSE, [
        ("Registros analizados", f"{len(df):,}", "Intervalos de 15 minutos del año completo."),
        ("Variables que entran al modelo", f"{enter} de {len(decisions)}",
         "Hora, día de la semana y tipo de carga entran; el resto queda fuera por redundancia o porque el gemelo no lo produce."),
        ("Efecto del tipo de carga", f"{kl['eps2']:.2f}", "Tamaño del efecto (de 0 a 1): cuánto del cambio de consumo se asocia al tipo de carga."),
        ("VIF del CO2", f"{vif.loc['CO2(tCO2)', 'VIF con CO2']:.0f}", help_text("VIF") + " Un valor alto indica que el CO2 casi copia al consumo."),
    ])

    tab_d, tab_g, tab_r, tab_m = st.tabs(["Resumen y decisión", "Diferencias entre grupos", "Redundancia y tiempo", "Entre modelos"])
    with tab_d:
        _summary_tab(t, decisions, kl, kh)
    with tab_g:
        _groups_tab(kl, mw)
    with tab_r:
        _redundancy_tab(t, vif)
    with tab_m:
        _model_tests()
    glossary_expander(["Valor p", "Kruskal-Wallis", "Dunn", "Mann-Whitney", "Spearman", "VIF", "KPSS", "TimeSeriesSplit",
                       "Friedman", "Nemenyi", "Diebold-Mariano"], "Glosario: pruebas estadísticas")
    next_step(4)


def _summary_tab(t: dict, decisions: pd.DataFrame, kl: dict, kh: dict) -> None:
    st.subheader("Decisión sobre las variables")
    st.dataframe(
        _style_decision(decisions.rename(columns={"variable": "Variable", "decisión": "Decisión", "evidencia": "Motivo y evidencia"})),
        hide_index=True, width="stretch")
    reading(
        "Entran hora, día y tipo de carga; quedan fuera reactiva, factor de potencia, NSM, WeekStatus y CO2.",
        "La decisión combina evidencia estadística (efecto grande de hora, día y carga) con la restricción de negocio: "
        "solo se usa lo que el gemelo puede producir.",
        "El siguiente paso, Preparación, construye un pipeline reproducible con estas tres variables y la semilla 42.",
    )
    st.subheader("Resultado de cada prueba")
    table = T.test_table(t).rename(columns={"prueba": "Prueba", "estadístico": "Estadístico", "p": "Valor p",
                                            "veredicto": "Veredicto", "lectura": "Qué encontró"})
    st.dataframe(table, hide_index=True, width="stretch")
    reading(
        f"Todas las pruebas de diferencia (Kruskal-Wallis y Mann-Whitney) dan p < 0.001 con 35,040 registros; "
        f"el tipo de carga explica una parte grande de la variación (efecto {kl['eps2']:.2f}) y la hora también ({kh['eps2']:.2f}).",
        "Con tantos datos casi cualquier diferencia sale significativa, por eso importa el tamaño del efecto y no solo el p: "
        "hora, carga y día separan el consumo de forma sustantiva, mientras que CO2 y kWh son casi la misma variable.",
        "Las tres variables del gemelo (hora, día, carga) están justificadas como entradas; las demás columnas se "
        "descartan por no poder producirse en el gemelo o por ser redundantes.",
    )


def _groups_tab(kl: dict, mw: dict) -> None:
    st.subheader("Consumo por tipo de carga (Kruskal-Wallis y Dunn)")
    dunn = kl["dunn"].rename(index=LOAD_SHORT, columns=LOAD_SHORT)
    fig = go.Figure(go.Heatmap(
        z=-np.log10(np.clip(dunn.to_numpy(dtype=float), 1e-300, 1.0)), x=list(dunn.columns), y=list(dunn.index),
        colorscale="Blues", colorbar=dict(title="Evidencia de<br>diferencia"),
        text=[["-" if i == j else fmt_p(v) for j, v in enumerate(row)] for i, row in enumerate(dunn.values)],
        texttemplate="%{text}", hovertemplate="%{y} frente a %{x}: valor p %{text}<extra></extra>"))
    style_fig(fig, "Valor p de Dunn entre cada par de tipos de carga", x="Tipo de carga", y="Tipo de carga", height=340, legend=False)
    fig.update_layout(margin=dict(t=64))
    show_fig(fig)
    med = kl["medians"]
    all_sig = bool(((dunn.values < 0.001) | (dunn.values == 1.0)).all())
    reading(
        f"H = {kl['H']:,.0f}, p < 0.001. Medianas: ligera {med['Light_Load']:.1f}, media {med['Medium_Load']:.1f} "
        f"y máxima {med['Maximum_Load']:.1f} kWh. En Dunn con Bonferroni "
        + ("los tres pares difieren con p < 0.001." if all_sig else "no todos los pares difieren."),
        "Los tres regímenes de carga son estadísticamente distintos entre sí, sin solaparse en la mediana.",
        "Se conserva el tipo de carga completo (tres niveles) y no se fusionan categorías.",
    )

    st.subheader("Día laborable frente a fin de semana (Mann-Whitney)")
    st.dataframe(pd.DataFrame([
        {"Grupo": "Lunes a viernes", "Registros": mw["n_weekday"], "Mediana (kWh)": mw["median_weekday"], "Media (kWh)": mw["mean_weekday"]},
        {"Grupo": "Sábado y domingo", "Registros": mw["n_weekend"], "Mediana (kWh)": mw["median_weekend"], "Media (kWh)": mw["mean_weekend"]}]),
        hide_index=True)
    reading(
        f"U = {mw['U']:,.0f}, p < 0.001; medias de {mw['mean_weekday']:.1f} kWh entre semana y {mw['mean_weekend']:.1f} kWh "
        f"en fin de semana; correlación biserial de rangos {mw['rank_biserial']:.2f}.",
        f"El consumo medio del fin de semana equivale a {mw['mean_weekend'] / mw['mean_weekday']:.0%} del de un día laborable.",
        "El día de la semana entra al modelo; el gemelo debe esperar demanda baja sábado y domingo.",
    )


def _redundancy_tab(t: dict, vif: pd.DataFrame) -> None:
    st.subheader("Por qué el CO2 no entra (VIF)")
    shown = t["vif"].round(1).copy()
    shown["variable"] = shown["variable"].map(lambda c: COLUMN_SHORT.get(c, c))
    st.dataframe(shown.rename(columns={"variable": "Variable", "VIF con CO2": "VIF con el CO2 en el conjunto",
                                       "VIF sin CO2": "VIF sin el CO2"}), hide_index=True)
    reading(
        f"Con el CO2 en el conjunto, el VIF del CO2 es {vif.loc['CO2(tCO2)', 'VIF con CO2']:.1f} y el del consumo "
        f"{vif.loc['Usage_kWh', 'VIF con CO2']:.1f}; sin CO2 el del consumo baja a {vif.loc['Usage_kWh', 'VIF sin CO2']:.1f}.",
        "Un VIF por encima de 10 indica que la variable se explica casi por completo con las demás: el CO2 y el "
        "consumo son redundantes entre sí.",
        "El CO2 queda fuera del modelo y se calcula después desde los kWh, para no inflar la precisión con una copia del objetivo.",
    )

    st.subheader("Por qué se valida en el tiempo (KPSS)")
    k = t["kpss"]
    st.dataframe(k.round(3).rename(columns={"hipótesis nula": "Hipótesis que se prueba", "estadístico": "Estadístico",
                                            "p (acotado a 0.01-0.10)": "Valor p (acotado a 0.01-0.10)", "rezagos": "Rezagos"}),
                 hide_index=True)
    rej = bool((k["p (acotado a 0.01-0.10)"] < 0.05).all())
    reading(
        f"El estadístico KPSS es {k.iloc[0]['estadístico']:.2f} (nivel) y {k.iloc[1]['estadístico']:.2f} (tendencia), con p en el "
        f"límite inferior de la tabla (0.01). La autocorrelación a 15 min es {t['acf']['lag1']:.2f} y a 24 h {t['acf']['lag96']:.2f}.",
        ("Se rechaza que la serie sea estacionaria: su nivel cambia con el tiempo, y las observaciones vecinas se parecen mucho."
         if rej else "No se rechaza la estacionariedad en todas las variantes; aun así la autocorrelación es alta."),
        "Se valida hacia adelante (entrenar en el pasado, examinar en el futuro) con TimeSeriesSplit; una partición aleatoria "
        "mezclaría vecinos casi idénticos y daría un error optimista.",
    )


def _model_tests() -> None:
    """Friedman/Nemenyi and Diebold-Mariano results between models (computed at training time)."""
    res = read_json("pruebas_modelos.json")
    if res is None:
        not_trained_message("Las pruebas entre modelos", button=False)
        return
    fn, dm = res["friedman_nemenyi"], res["diebold_mariano"]

    def verdict(p: float) -> str:
        return "✅ Diferencia significativa" if p < 0.05 else "⚠️ Sin diferencia significativa"

    rows = [{"Prueba": "Friedman sobre el MAE semanal del examen", "Estadístico": f"chi² = {fn['chi2']:.2f}",
             "Valor p": fmt_p(fn["p"]), "Veredicto": verdict(fn["p"]),
             "Qué encontró": "Rangos medios: " + ", ".join(f"{k} {v:.2f}" for k, v in fn["mean_ranks"].items())}]
    models = list(fn["mean_ranks"])
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            p = fn["nemenyi"][a][b]
            rows.append({"Prueba": f"Nemenyi: {a} frente a {b}", "Estadístico": "-", "Valor p": fmt_p(p), "Veredicto": verdict(p),
                         "Qué encontró": "Difieren" if p < 0.05 else "No se distinguen"})
    for r in dm:
        rows.append({"Prueba": f"Diebold-Mariano (diciembre): {r['model_a']} frente a {r['model_b']}", "Estadístico": f"DM = {r['stat']:.2f}",
                     "Valor p": fmt_p(r["p"]), "Veredicto": verdict(r["p"]),
                     "Qué encontró": f"Diferencia media de error {r['mean_diff']:+.2f} kWh (negativa: {r['model_a']} mejor)"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    reading(
        f"Friedman con {fn['n_windows']} semanas: p {'< 0.001' if fn['p'] < 0.001 else round(fn['p'], 3)}. "
        + " ".join(f"XGBoost frente a {r['model_b']}: p {r['p']:.3g}." for r in dm),
        "Friedman y Nemenyi ordenan los modelos por su error semanal; Diebold-Mariano contrasta las predicciones de diciembre con una "
        "varianza robusta a la autocorrelación.",
        "El detalle y las figuras están en Evaluación; aquí queda el registro de que la elección del modelo se apoya en pruebas y no solo en un promedio.",
    )
