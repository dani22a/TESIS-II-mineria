"""Phase 7 - Evaluación: exam metrics, tests between models and explainability."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import pipeline
from lab.config import ARTIFACTS, DAYS_ES, LOAD_COLORS, LOAD_ES, LOAD_SHORT, LOAD_TYPES, MODEL_COLORS, MODELS
from lab.glossary import help_text
from lab.theme import ACCENT, NEGATIVE, POSITIVE, feature_label, style_fig
from lab.ui import (fmt_p, glossary_expander, next_step, not_trained_message, page_header, read_json, reading,
                    show_fig, train_all_button)

PURPOSE = ("Mide los tres modelos en el trimestre de examen que no se usó para ajustar, compara sus errores "
           "y muestra qué variables pesan en cada predicción.")


def _results_card(m: dict) -> None:
    """Three models side by side; the lowest MAE is highlighted and MAE is the headline metric."""
    per = m["per_model"]
    best = min(per, key=lambda k: per[k]["mae"])
    st.subheader("Tarjeta de resultados en el examen")
    st.caption("Error medio de cada modelo en octubre a diciembre. El mejor MAE es el criterio para elegir el modelo que se exporta.")
    for col, name in zip(st.columns(len(MODELS)), MODELS):
        v = per[name]
        is_best = name == best
        with col.container(border=True, key=f"winner_{name.replace(' ', '_')}" if is_best else f"card_{name.replace(' ', '_')}"):
            st.markdown(f"**{name}**")
            if is_best:
                st.badge("Mejor MAE", icon=":material/emoji_events:", color="green")
            else:
                st.badge("Comparado", color="gray")
            st.metric("MAE (kWh / 15 min)", f"{v['mae']:.2f}", help=help_text("MAE"),
                      delta=None if is_best else f"+{v['mae'] - per[best]['mae']:.2f} kWh frente al mejor",
                      delta_color="inverse")
            st.markdown(f"RMSE: **{v['rmse']:.2f} kWh**  \nMAPE: **{v['mape']:.1f} %**  \nR²: **{v['r2']:.2f}**")


def _metrics_section(m: dict) -> None:
    per, exported = m["per_model"], m["exported"]
    tbl = pd.DataFrame([{"Modelo": k, "MAE (kWh)": v["mae"], "RMSE (kWh)": v["rmse"], "MAPE (%)": v["mape"], "R²": v["r2"]}
                        for k, v in per.items()]).sort_values("MAE (kWh)")
    st.dataframe(tbl.round(3), hide_index=True, width="stretch",
                 column_config={"MAE (kWh)": st.column_config.NumberColumn(help=help_text("MAE")),
                                "RMSE (kWh)": st.column_config.NumberColumn(help=help_text("RMSE")),
                                "MAPE (%)": st.column_config.NumberColumn(help=help_text("MAPE")),
                                "R²": st.column_config.NumberColumn(help=help_text("R²"))})
    fig = go.Figure(go.Bar(x=tbl["Modelo"], y=tbl["MAE (kWh)"], marker_color=[MODEL_COLORS[x] for x in tbl["Modelo"]],
                           text=tbl["MAE (kWh)"].round(2), textposition="outside",
                           hovertemplate="%{x}: MAE %{y:.2f} kWh<extra></extra>"))
    style_fig(fig, "Error medio (MAE) de cada modelo en el examen", x="Modelo", y="MAE en el examen (kWh / 15 min)", height=340, legend=False)
    fig.update_layout(margin=dict(t=64))
    show_fig(fig)
    best, worst = tbl.iloc[0], tbl.iloc[-1]
    mean_y = per[exported]["mae"]
    reading(
        "MAE: " + ", ".join(f"{r['Modelo']} {r['MAE (kWh)']:.2f}" for _, r in tbl.iterrows())
        + f" kWh; R² entre {tbl['R²'].min():.2f} y {tbl['R²'].max():.2f}. El menor MAE es {best['Modelo']}, con RMSE {best['RMSE (kWh)']:.2f} kWh.",
        f"{best['Modelo']} se equivoca en promedio {best['MAE (kWh)']:.1f} kWh por intervalo de 15 min, {worst['MAE (kWh)'] - best['MAE (kWh)']:.1f} kWh menos que "
        f"{worst['Modelo']}. El MAPE ({best['MAPE (%)']:.0f} % en el mejor) se calcula solo con consumos de 1 kWh o más, porque los valores cercanos a cero lo inflan.",
        f"Se exporta {exported} al gemelo por tener el menor MAE en un trimestre que no se usó para ajustar; su error típico "
        f"({mean_y:.1f} kWh) es el margen que el gemelo debe considerar al mostrar la electricidad de planta.",
    )


def _week_section() -> None:
    path = ARTIFACTS / pipeline.PREDICTIONS
    if not path.exists():
        st.info("La comparación semanal necesita `artefactos/predicciones_examen.csv`, que se genera al entrenar.")
        return
    p = pd.read_csv(path, parse_dates=["ts_start"])
    start = pd.Timestamp("2018-10-08")
    w = p[(p["ts_start"] >= start) & (p["ts_start"] < start + pd.Timedelta(days=7))]
    fig = go.Figure(go.Scatter(x=w["ts_start"], y=w["y"], name="Consumo real", line=dict(color="#222", width=1.8)))
    for mname in MODELS:
        fig.add_trace(go.Scatter(x=w["ts_start"], y=w[mname], name=mname, line=dict(color=MODEL_COLORS[mname], width=1.2)))
    style_fig(fig, "Consumo real y predicho en la semana del 8 al 14 de octubre", x="Fecha", y="Consumo (kWh / 15 min)", height=400)
    fig.update_layout(hovermode="x unified")
    show_fig(fig)
    mae = {mname: float(np.abs(w["y"] - w[mname]).mean()) for mname in MODELS}
    resid_h = p.assign(err=np.abs(p["y"] - p["XGBoost"])).groupby(p["hour_frac"].astype(int))["err"].mean()
    hard = int(resid_h.idxmax())
    reading(
        "Semana del 8 al 14 de octubre: MAE de " + ", ".join(f"{k} {v:.1f}" for k, v in mae.items())
        + f" kWh. Sobre todo el examen, XGBoost falla más a las {hard:02d}h ({resid_h.max():.1f} kWh de error medio).",
        "Los modelos siguen los turnos (subida a las 08h, caída de mediodía, bajada nocturna) pero no el nivel exacto de "
        "cada día, porque hora, día y tipo de carga no informan cuánta producción hubo realmente ese día.",
        "Para el gemelo, la predicción sirve como patrón esperado del turno; una desviación sostenida frente a ese patrón "
        "señala una operación distinta de la habitual.",
    )


def _tests_section(t: dict, windows: list[dict]) -> None:
    fn, dm = t["friedman_nemenyi"], t["diebold_mariano"]
    st.subheader("Error semanal por modelo")
    w = pd.DataFrame(windows)
    fig = go.Figure()
    for mname in MODELS:
        fig.add_trace(go.Scatter(x=w["start"], y=w[mname], name=mname, mode="lines+markers", line=dict(color=MODEL_COLORS[mname])))
    style_fig(fig, "Error (MAE) de cada modelo en cada semana del examen", x="Inicio de la semana", y="MAE semanal (kWh / 15 min)", height=360)
    fig.update_layout(hovermode="x unified")
    show_fig(fig)
    wins = {mname: int((w[MODELS].idxmin(axis=1) == mname).sum()) for mname in MODELS}
    reading(
        f"{fn['n_windows']} semanas completas del examen. Semanas ganadas (menor MAE): " + ", ".join(f"{k} {v}" for k, v in wins.items()) + ".",
        "Cada semana es una réplica del examen; contar cuántas veces gana cada modelo es más robusto que un solo promedio.",
        "Si un modelo gana de forma consistente, la decisión de exportarlo no depende de una semana atípica.",
    )

    st.subheader("Friedman y Nemenyi sobre el MAE semanal")
    ranks = pd.DataFrame({"Modelo": list(fn["mean_ranks"]), "Rango medio (1 = mejor)": list(fn["mean_ranks"].values())}).sort_values("Rango medio (1 = mejor)")
    st.dataframe(ranks.round(2), hide_index=True)
    nem = pd.DataFrame(fn["nemenyi"]).loc[MODELS, MODELS]
    fig = go.Figure(go.Heatmap(z=nem.values, x=MODELS, y=MODELS, zmin=0, zmax=1, colorscale="Blues_r",
                               colorbar=dict(title="Valor p"),
                               text=[[f"{v:.3f}" for v in r] for r in nem.values], texttemplate="%{text}",
                               hovertemplate="%{y} frente a %{x}: valor p %{text}<extra></extra>"))
    style_fig(fig, "Valor p de Nemenyi entre cada par de modelos (oscuro: difieren)", x="Modelo", y="Modelo", height=340, legend=False)
    fig.update_layout(margin=dict(t=64))
    show_fig(fig)
    pairs = [(a, b) for i, a in enumerate(MODELS) for b in MODELS[i + 1:]]
    sig = [f"{a} frente a {b}" for a, b in pairs if nem.loc[a, b] < 0.05]
    reading(
        f"Friedman: chi² = {fn['chi2']:.2f}, p {fmt_p(fn['p'])} con {fn['n_windows']} semanas. Rangos medios: "
        + ", ".join(f"{k} {v:.2f}" for k, v in sorted(fn["mean_ranks"].items(), key=lambda kv: kv[1]))
        + ". Pares con p de Nemenyi menor a 0.05: " + (", ".join(sig) if sig else "ninguno") + ".",
        ("Los modelos no rinden igual semana a semana; el posthoc identifica qué pares difieren." if fn["p"] < 0.05
         else "No hay evidencia de que los modelos difieran de forma consistente semana a semana.")
        + (" Los pares no listados no se distinguen con solo " + str(fn['n_windows']) + " semanas." if sig and len(sig) < len(pairs) else ""),
        "El ranking por semanas respalda (o matiza) la elección por MAE global; si dos modelos no se distinguen, se puede "
        "preferir el más simple de explicar.",
    )

    st.subheader("Diebold-Mariano en diciembre (XGBoost frente a cada rival)")
    d = pd.DataFrame([{"Comparación": f"{r['model_a']} frente a {r['model_b']}", "Registros": r["n"], "MAE A (kWh)": r["mae_a"], "MAE B (kWh)": r["mae_b"],
                       "Diferencia media (kWh)": r["mean_diff"], "Estadístico DM": r["stat"], "Valor p (Newey-West)": r["p"],
                       "Valor p (rezago de 1 día)": r["p_lag96"]} for r in dm])
    st.dataframe(d.round(4), hide_index=True, width="stretch")
    lines = []
    for r in dm:
        who = r["model_a"] if r["mean_diff"] < 0 else r["model_b"]
        lines.append(f"contra {r['model_b']}, {who} tiene menor error absoluto ({abs(r['mean_diff']):.2f} kWh de diferencia, p {fmt_p(r['p'])}; con rezago de un día p {fmt_p(r['p_lag96'])})")
    reading(
        "Sobre las " + f"{dm[0]['n']:,}" + " predicciones de diciembre: " + "; ".join(lines) + ".",
        "La pérdida es el error absoluto; el estadístico DM usa una varianza robusta a la autocorrelación (Newey-West). "
        "Un p pequeño indica que la diferencia de error entre los modelos no es ruido del mes.",
        "Si la diferencia no es significativa, la elección entre esos dos modelos es de simplicidad y costo; si lo es, "
        "se justifica la complejidad del ganador.",
    )


def _explain_section(e: dict) -> None:
    tab_en, tab_rf, tab_shap = st.tabs(["Elastic Net: coeficientes", "Random Forest: importancias", "XGBoost: SHAP"])

    with tab_en:
        coef = pd.DataFrame(e["elastic_net_coefficients"])
        c = coef[coef["feature"] != "(intercepto)"].sort_values("coef")
        fig = go.Figure(go.Bar(x=c["coef"], y=[feature_label(f) for f in c["feature"]], orientation="h",
                               marker_color=[POSITIVE if v > 0 else NEGATIVE for v in c["coef"]],
                               hovertemplate="%{y}: %{x:+.2f} kWh<extra></extra>"))
        style_fig(fig, "Efecto de cada columna sobre el consumo (rojo sube, azul baja)", x="Coeficiente (kWh por desviación estándar)", y=None,
                  height=440, legend=False)
        show_fig(fig)
        top = c.reindex(c["coef"].abs().sort_values(ascending=False).index).head(3)
        reading(
            "Mayores coeficientes: " + ", ".join(f"{feature_label(r.feature)} ({r.coef:+.2f})" for r in top.itertuples())
            + f". Intercepto {coef.iloc[-1]['coef']:.1f} kWh.",
            "Cada coeficiente es el cambio en kWh al subir una desviación estándar de esa columna, manteniendo el resto; "
            "el signo indica si empuja el consumo hacia arriba o abajo. Es la lectura más directa, pero solo suma efectos y no cruza carga con hora.",
            "Sirve como línea base explicable: la carga máxima y las horas de turno explican más que el día suelto.",
        )
    with tab_rf:
        imp = pd.DataFrame(e["random_forest_importances"]).sort_values("importance")
        fig = go.Figure(go.Bar(x=imp["importance"], y=[feature_label(f) for f in imp["feature"]], orientation="h",
                               marker_color=MODEL_COLORS["Random Forest"], hovertemplate="%{y}: %{x:.3f}<extra></extra>"))
        style_fig(fig, "Peso de cada columna en los árboles del Random Forest", x="Importancia (reducción de impureza, suma 1)", y=None,
                  height=440, legend=False, hover=".3f")
        show_fig(fig)
        top = imp.iloc[::-1].head(3)
        reading(
            "Mayores importancias: " + ", ".join(f"{feature_label(r.feature)} ({r.importance:.2f})" for r in top.itertuples()) + ".",
            "La importancia mide cuánto reduce el error cada columna al partir los árboles; no indica el sentido del efecto, solo el peso.",
            "Confirma qué señales del gemelo son críticas: si falla una de las de mayor peso, la predicción se degrada más.",
        )
    with tab_shap:
        _shap_tab(e)


def _shap_tab(e: dict) -> None:
    st.caption(help_text("SHAP"))
    g = pd.DataFrame(e["xgboost_shap_global"]).sort_values("mean_abs_shap")
    fig = go.Figure(go.Bar(x=g["mean_abs_shap"], y=[feature_label(f) for f in g["feature"]], orientation="h",
                           marker_color=MODEL_COLORS["XGBoost"], hovertemplate="%{y}: %{x:.1f} kWh<extra></extra>"))
    style_fig(fig, "Peso medio de cada columna en las predicciones de XGBoost", x="Aporte medio absoluto (SHAP, kWh)", y=None,
              height=440, legend=False, hover=".1f")
    show_fig(fig)
    top = g.iloc[::-1].head(3)
    reading(
        "Mayor |SHAP| medio: " + ", ".join(f"{feature_label(r.feature)} ({r.mean_abs_shap:.1f} kWh)" for r in top.itertuples())
        + f"; valor base {e['xgboost_shap_base_value']:.1f} kWh.",
        "SHAP reparte la diferencia entre cada predicción y el promedio de la planta entre las columnas; la barra es cuánto pesa cada una en promedio.",
        "Los aportes globales indican dónde mirar primero al explicar un consumo alto o bajo en la planta.",
    )
    sample_path = ARTIFACTS / pipeline.SHAP_SAMPLE
    if sample_path.exists():
        with st.expander("Detalle: dispersión de los aportes SHAP por registro", icon=":material/scatter_plot:"):
            import matplotlib.pyplot as plt
            import shap

            sample = pd.read_csv(sample_path)
            names = [c[5:] for c in sample.columns if c.startswith("shap_")]
            sv = sample[[f"shap_{n}" for n in names]].to_numpy()
            plt.figure(figsize=(8, 5))
            shap.summary_plot(sv, sample[names], feature_names=[feature_label(n) for n in names], show=False)
            st.pyplot(plt.gcf(), clear_figure=True)
            reading(
                f"Resumen de {len(sample):,} registros del examen: cada punto es un intervalo; el color va del valor bajo (azul) al alto (rojo) de la columna.",
                "Se ve, por ejemplo, si la carga máxima (rojo en su columna) empuja siempre hacia kWh altos y cuánto se dispersa el efecto de la hora.",
                "Un efecto muy disperso indica que la señal actúa solo en interacción con otras (turno y carga a la vez).",
            )
    else:
        st.caption("El gráfico de puntos de SHAP necesita artefactos/shap_muestra.csv (se genera al entrenar).")

    dep = e["dependence_hour"]
    fig = go.Figure()
    for lt in LOAD_TYPES:
        fig.add_trace(go.Scatter(x=dep["hour_frac"], y=dep["series"][lt], mode="lines", name=LOAD_SHORT[lt], line=dict(color=LOAD_COLORS[lt]),
                                 connectgaps=False))
    fig.add_trace(go.Scatter(x=dep["hour_frac"], y=dep["all"], mode="lines", name="Todas las cargas", line=dict(color="#333", dash="dot")))
    style_fig(fig, "Aporte de la hora del día al consumo, por tipo de carga", x="Hora del día", y="Aporte SHAP de la hora (kWh)", height=380)
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(dtick=2)
    show_fig(fig)
    allv = np.array(dep["all"])
    hh = np.array(dep["hour_frac"])
    hi, lo = hh[allv.argmax()], hh[allv.argmin()]
    reading(
        f"El aporte medio de la hora va de {allv.min():+.1f} kWh (a las {int(lo):02d}:{int(round((lo % 1) * 60)):02d}) a {allv.max():+.1f} kWh (a las {int(hi):02d}:{int(round((hi % 1) * 60)):02d}).",
        "Es el efecto de la hora del día sobre el consumo, separado del de carga y día: los turnos de trabajo suman y la madrugada resta.",
        "El gemelo puede explicar un consumo esperado con la hora sola: por ejemplo, cuánto del kWh se debe al turno y cuánto al tipo de carga.",
    )

    w = e["waterfall"]
    feats = pd.DataFrame(w["features"])
    feats = feats.reindex(feats["shap"].abs().sort_values(ascending=False).index)
    top, rest = feats.head(6), feats.iloc[6:]
    labels = [feature_label(f) for f in top["feature"]] + (["Otras columnas"] if len(rest) else [])
    vals = list(top["shap"]) + ([float(rest["shap"].sum())] if len(rest) else [])
    fig = go.Figure(go.Waterfall(x=["Promedio de la planta"] + labels + ["Predicción"], y=[w["base_value"]] + vals + [0],
                                 measure=["absolute"] + ["relative"] * len(vals) + ["total"],
                                 connector={"line": {"color": "#999"}}, increasing=dict(marker_color=POSITIVE),
                                 decreasing=dict(marker_color=NEGATIVE), totals=dict(marker_color=ACCENT)))
    style_fig(fig, "Cómo se construye una predicción concreta, paso a paso", x=None, y="Consumo (kWh / 15 min)", height=400, legend=False)
    fig.update_layout(margin=dict(t=64))
    show_fig(fig)
    case = w["case"]
    gc = w["group_contributions"]
    reading(
        f"Caso: {DAYS_ES[case['day']].lower()} a las {int(case['hour']):02d}:00 con {LOAD_ES[case['load_type']].lower()}. Se parte del promedio de {w['base_value']:.1f} kWh "
        f"y se llega a {w['prediction']:.1f} kWh: carga {gc['load_type']:+.1f}, hora {gc['hour']:+.1f} y día {gc['day']:+.1f} kWh.",
        "Cada barra suma o resta kWh al promedio; la cascada muestra cómo el modelo construye una predicción concreta paso a paso.",
        "Sirve para justificar ante el operador por qué el gemelo muestra ese consumo en un turno específico.",
    )


def render() -> None:
    m = read_json(pipeline.METRICS)
    if m is None:
        page_header(7, PURPOSE, [("Modelo exportado", "Sin entrenar", "Se define al entrenar: es el de menor MAE en el examen."),
                                 ("MAE en el examen", "-", help_text("MAE")),
                                 ("RMSE en el examen", "-", help_text("RMSE")),
                                 ("R² en el examen", "-", help_text("R²"))])
        not_trained_message("La evaluación")
        train_all_button("btn_eval", expanded=True)
        glossary_expander(["MAE", "RMSE", "MAPE", "R²"], "Glosario: métricas de error")
        next_step(7)
        return

    exported = m["exported"]
    x = m["per_model"][exported]
    page_header(7, PURPOSE, [
        ("Modelo a exportar", exported, "El de menor MAE en el examen."),
        ("MAE en el examen", f"{x['mae']:.2f} kWh", help_text("MAE")),
        ("RMSE en el examen", f"{x['rmse']:.2f} kWh", help_text("RMSE")),
        ("R² en el examen", f"{x['r2']:.2f}", help_text("R²")),
    ])
    _results_card(m)

    t, w = read_json(pipeline.MODEL_TESTS), read_json(pipeline.WINDOWS)
    e = read_json(pipeline.EXPLAIN)
    tab_c, tab_w, tab_t, tab_e, tab_d = st.tabs(["Comparación", "Real frente a predicho", "Pruebas entre modelos",
                                                  "Explicabilidad", "Modelo elegido"])
    with tab_c:
        _metrics_section(m)
    with tab_w:
        _week_section()
    with tab_t:
        if t and w:
            _tests_section(t, w)
        else:
            not_trained_message("Las pruebas entre modelos")
    with tab_e:
        if e:
            _explain_section(e)
        else:
            not_trained_message("La explicabilidad")
    with tab_d:
        st.success(f"Modelo exportado: {exported} (menor MAE en el examen: {x['mae']:.2f} kWh).", icon=":material/check_circle:")
        reading(
            f"{exported} obtiene el menor MAE del examen ({x['mae']:.2f} kWh); los tres modelos se entrenaron con los mismos datos y la misma semilla.",
            "La regla de decisión es el MAE del último trimestre, que no participó en el ajuste; las pruebas de Friedman y Diebold-Mariano indican si "
            "la ventaja es sólida o pequeña.",
            "Ese modelo alimenta la tabla del artefacto que lee el gemelo; la pantalla Despliegue permite probar escenarios y descargar el JSON.",
        )
    train_all_button("btn_eval")
    glossary_expander(["MAE", "RMSE", "MAPE", "R²", "Friedman", "Nemenyi", "Diebold-Mariano", "SHAP"], "Glosario: métricas y pruebas")
    next_step(7)
