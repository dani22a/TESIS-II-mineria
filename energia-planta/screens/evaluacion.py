"""Phase 7 - Evaluación: exam metrics, tests between models and explainability."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab import pipeline
from lab.config import ARTIFACTS, DAYS_ES, LOAD_COLORS, LOAD_ES, LOAD_TYPES, MODELS
from lab.ui import not_trained_message, read_json, reading, train_all_button

MODEL_COLORS = {"Elastic Net": "#7f7f7f", "Random Forest": "#2ca02c", "XGBoost": "#1f77b4"}


def _fmt_p(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def _metrics_section(m: dict) -> None:
    per, exported = m["per_model"], m["exported"]
    st.subheader("Métricas en el examen (octubre a diciembre)")
    tbl = pd.DataFrame([{"modelo": k, "MAE (kWh)": v["mae"], "RMSE (kWh)": v["rmse"], "MAPE (%)": v["mape"], "R²": v["r2"]}
                        for k, v in per.items()]).sort_values("MAE (kWh)")
    st.dataframe(tbl.round(3), hide_index=True, width="stretch")
    fig = go.Figure(go.Bar(x=tbl["modelo"], y=tbl["MAE (kWh)"], marker_color=[MODEL_COLORS[x] for x in tbl["modelo"]],
                           text=tbl["MAE (kWh)"].round(2), textposition="outside"))
    fig.update_layout(template="plotly_white", height=320, yaxis_title="MAE en el examen (kWh)")
    st.plotly_chart(fig, width="stretch")
    best, worst = tbl.iloc[0], tbl.iloc[-1]
    mean_y = per[exported]["mae"]
    reading(
        f"MAE: " + ", ".join(f"{r['modelo']} {r['MAE (kWh)']:.2f}" for _, r in tbl.iterrows())
        + f" kWh; R² entre {tbl['R²'].min():.2f} y {tbl['R²'].max():.2f}. El menor MAE es {best['modelo']}, con RMSE {best['RMSE (kWh)']:.2f} kWh.",
        f"{best['modelo']} se equivoca en promedio {best['MAE (kWh)']:.1f} kWh por intervalo de 15 min, {worst['MAE (kWh)'] - best['MAE (kWh)']:.1f} kWh menos que "
        f"{worst['modelo']}. El MAPE ({best['MAPE (%)']:.0f} % en el mejor) se calcula solo con consumos de 1 kWh o más, porque los valores cercanos a cero lo inflan.",
        f"Se exporta {exported} al gemelo por tener el menor MAE en un trimestre que no se usó para ajustar; su error típico "
        f"({mean_y:.1f} kWh) es el margen que el gemelo debe considerar al mostrar la electricidad de planta.",
    )


def _week_section() -> None:
    path = ARTIFACTS / pipeline.PREDICTIONS
    if not path.exists():
        return
    st.subheader("Real frente a predicho en una semana del examen")
    p = pd.read_csv(path, parse_dates=["ts_start"])
    start = pd.Timestamp("2018-10-08")
    w = p[(p["ts_start"] >= start) & (p["ts_start"] < start + pd.Timedelta(days=7))]
    fig = go.Figure(go.Scatter(x=w["ts_start"], y=w["y"], name="Real", line=dict(color="#222", width=1.5)))
    for m in MODELS:
        fig.add_trace(go.Scatter(x=w["ts_start"], y=w[m], name=m, line=dict(color=MODEL_COLORS[m], width=1)))
    fig.update_layout(template="plotly_white", height=380, yaxis_title="kWh por 15 min", legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    mae = {m: float(np.abs(w["y"] - w[m]).mean()) for m in MODELS}
    resid_h = p.assign(err=np.abs(p["y"] - p["XGBoost"])).groupby(p["hour_frac"].astype(int))["err"].mean()
    hard = int(resid_h.idxmax())
    reading(
        "Semana del 8 al 14 de octubre: MAE de " + ", ".join(f"{m} {v:.1f}" for m, v in mae.items())
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
    for m in MODELS:
        fig.add_trace(go.Scatter(x=w["start"], y=w[m], name=m, mode="lines+markers", line=dict(color=MODEL_COLORS[m])))
    fig.update_layout(template="plotly_white", height=340, yaxis_title="MAE semanal (kWh)", legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    wins = {m: int((w[MODELS].idxmin(axis=1) == m).sum()) for m in MODELS}
    reading(
        f"{fn['n_windows']} semanas completas del examen. Semanas ganadas (menor MAE): " + ", ".join(f"{m} {v}" for m, v in wins.items()) + ".",
        "Cada semana es una réplica del examen; contar cuántas veces gana cada modelo es más robusto que un solo promedio.",
        "Si un modelo gana de forma consistente, la decisión de exportarlo no depende de una semana atípica.",
    )

    st.subheader("Friedman y Nemenyi sobre el MAE semanal")
    ranks = pd.DataFrame({"modelo": list(fn["mean_ranks"]), "rango medio (1 = mejor)": list(fn["mean_ranks"].values())}).sort_values("rango medio (1 = mejor)")
    st.dataframe(ranks.round(2), hide_index=True)
    nem = pd.DataFrame(fn["nemenyi"]).loc[MODELS, MODELS]
    fig = go.Figure(go.Heatmap(z=nem.values, x=MODELS, y=MODELS, zmin=0, zmax=1, colorscale="Blues_r",
                               text=[[f"{v:.3f}" for v in r] for r in nem.values], texttemplate="%{text}"))
    fig.update_layout(template="plotly_white", height=320, title="p de Nemenyi entre pares")
    st.plotly_chart(fig, width="stretch")
    pairs = [(a, b) for i, a in enumerate(MODELS) for b in MODELS[i + 1:]]
    sig = [f"{a} vs {b}" for a, b in pairs if nem.loc[a, b] < 0.05]
    reading(
        f"Friedman: chi² = {fn['chi2']:.2f}, p {_fmt_p(fn['p'])} con {fn['n_windows']} semanas. Rangos medios: "
        + ", ".join(f"{k} {v:.2f}" for k, v in sorted(fn["mean_ranks"].items(), key=lambda kv: kv[1]))
        + ". Pares con p de Nemenyi menor a 0.05: " + (", ".join(sig) if sig else "ninguno") + ".",
        ("Los modelos no rinden igual semana a semana; el posthoc identifica qué pares difieren." if fn["p"] < 0.05
         else "No hay evidencia de que los modelos difieran de forma consistente semana a semana.")
        + (" Los pares no listados no se distinguen con solo " + str(fn['n_windows']) + " semanas." if sig and len(sig) < len(pairs) else ""),
        "El ranking por semanas respalda (o matiza) la elección por MAE global; si dos modelos no se distinguen, se puede "
        "preferir el más simple de explicar.",
    )

    st.subheader("Diebold-Mariano en diciembre (XGBoost frente a cada rival)")
    d = pd.DataFrame([{"comparación": f"{r['model_a']} vs {r['model_b']}", "registros": r["n"], "MAE A (kWh)": r["mae_a"], "MAE B (kWh)": r["mae_b"],
                       "diferencia media (kWh)": r["mean_diff"], "estadístico DM": r["stat"], "p (Newey-West)": r["p"],
                       "p (rezago de 1 día)": r["p_lag96"]} for r in dm])
    st.dataframe(d.round(4), hide_index=True, width="stretch")
    lines = []
    for r in dm:
        who = r["model_a"] if r["mean_diff"] < 0 else r["model_b"]
        lines.append(f"contra {r['model_b']}, {who} tiene menor error absoluto ({abs(r['mean_diff']):.2f} kWh de diferencia, p {_fmt_p(r['p'])}; con rezago de un día p {_fmt_p(r['p_lag96'])})")
    reading(
        "Sobre las " + f"{dm[0]['n']:,}" + " predicciones de diciembre: " + "; ".join(lines) + ".",
        "La pérdida es el error absoluto; el estadístico DM usa una varianza robusta a la autocorrelación (Newey-West). "
        "Un p pequeño indica que la diferencia de error entre los modelos no es ruido del mes.",
        "Si la diferencia no es significativa, la elección entre esos dos modelos es de simplicidad y costo; si lo es, "
        "se justifica la complejidad del ganador.",
    )


def _explain_section(e: dict, m: dict) -> None:
    st.subheader("Explicabilidad")
    tab_en, tab_rf, tab_shap = st.tabs(["Elastic Net (coeficientes)", "Random Forest (importancias)", "XGBoost (SHAP)"])

    with tab_en:
        coef = pd.DataFrame(e["elastic_net_coefficients"])
        c = coef[coef["feature"] != "(intercepto)"].sort_values("coef")
        fig = go.Figure(go.Bar(x=c["coef"], y=c["feature"], orientation="h", marker_color=["#d64550" if v > 0 else "#4c9be8" for v in c["coef"]]))
        fig.update_layout(template="plotly_white", height=420, xaxis_title="Coeficiente (variables estandarizadas, kWh)")
        st.plotly_chart(fig, width="stretch")
        top = c.reindex(c["coef"].abs().sort_values(ascending=False).index).head(3)
        reading(
            "Mayores coeficientes: " + ", ".join(f"{r.feature} ({r.coef:+.2f})" for r in top.itertuples())
            + f". Intercepto {coef.iloc[-1]['coef']:.1f} kWh.",
            "Cada coeficiente es el cambio en kWh al subir una desviación estándar de esa columna, manteniendo el resto; "
            "el signo indica si empuja el consumo hacia arriba o abajo. Es la lectura más directa, pero solo suma efectos y no cruza carga con hora.",
            "Sirve como línea base explicable: la carga máxima y las horas de turno explican más que el día suelto.",
        )
    with tab_rf:
        imp = pd.DataFrame(e["random_forest_importances"]).sort_values("importance")
        fig = go.Figure(go.Bar(x=imp["importance"], y=imp["feature"], orientation="h", marker_color="#2ca02c"))
        fig.update_layout(template="plotly_white", height=420, xaxis_title="Importancia (reducción de impureza)")
        st.plotly_chart(fig, width="stretch")
        top = imp.iloc[::-1].head(3)
        reading(
            "Mayores importancias: " + ", ".join(f"{r.feature} ({r.importance:.2f})" for r in top.itertuples()) + ".",
            "La importancia mide cuánto reduce el error cada columna al partir los árboles; no indica el sentido del efecto, solo el peso.",
            "Confirma qué señales del gemelo son críticas: si falla una de las de mayor peso, la predicción se degrada más.",
        )
    with tab_shap:
        g = pd.DataFrame(e["xgboost_shap_global"]).sort_values("mean_abs_shap")
        fig = go.Figure(go.Bar(x=g["mean_abs_shap"], y=g["feature"], orientation="h", marker_color="#1f77b4"))
        fig.update_layout(template="plotly_white", height=420, xaxis_title="|SHAP| medio (kWh) en el examen")
        st.plotly_chart(fig, width="stretch")
        top = g.iloc[::-1].head(3)
        reading(
            "Mayor |SHAP| medio: " + ", ".join(f"{r.feature} ({r.mean_abs_shap:.1f} kWh)" for r in top.itertuples())
            + f"; valor base {e['xgboost_shap_base_value']:.1f} kWh.",
            "SHAP reparte la diferencia entre cada predicción y el promedio de la planta entre las columnas; la barra es cuánto pesa cada una en promedio.",
            "Los aportes globales indican dónde mirar primero al explicar un consumo alto o bajo en la planta.",
        )
        sample_path = ARTIFACTS / pipeline.SHAP_SAMPLE
        if sample_path.exists():
            import matplotlib.pyplot as plt
            import shap

            sample = pd.read_csv(sample_path)
            names = [c[5:] for c in sample.columns if c.startswith("shap_")]
            sv = sample[[f"shap_{n}" for n in names]].to_numpy()
            plt.figure(figsize=(8, 5))
            shap.summary_plot(sv, sample[names], feature_names=names, show=False)
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
            fig.add_trace(go.Scatter(x=dep["hour_frac"], y=dep["series"][lt], mode="lines", name=LOAD_ES[lt], line=dict(color=LOAD_COLORS[lt]),
                                     connectgaps=False))
        fig.add_trace(go.Scatter(x=dep["hour_frac"], y=dep["all"], mode="lines", name="Todas", line=dict(color="#333", dash="dot")))
        fig.update_layout(template="plotly_white", height=360, xaxis_title="Hora del día", yaxis_title="Aporte SHAP de la hora (kWh)")
        st.plotly_chart(fig, width="stretch")
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
        labels = list(top["feature"]) + (["otras columnas"] if len(rest) else [])
        vals = list(top["shap"]) + ([float(rest["shap"].sum())] if len(rest) else [])
        fig = go.Figure(go.Waterfall(x=["Promedio de la planta"] + labels + ["Predicción"], y=[w["base_value"]] + vals + [0],
                                     measure=["absolute"] + ["relative"] * len(vals) + ["total"],
                                     connector={"line": {"color": "#999"}}, increasing=dict(marker_color="#d64550"),
                                     decreasing=dict(marker_color="#4c9be8"), totals=dict(marker_color="#1f77b4")))
        fig.update_layout(template="plotly_white", height=380, yaxis_title="kWh por 15 min")
        st.plotly_chart(fig, width="stretch")
        case = w["case"]
        gc = w["group_contributions"]
        reading(
            f"Caso: {DAYS_ES[case['day']].lower()} a las {int(case['hour']):02d}:00 con {LOAD_ES[case['load_type']].lower()}. Se parte del promedio de {w['base_value']:.1f} kWh "
            f"y se llega a {w['prediction']:.1f} kWh: carga {gc['load_type']:+.1f}, hora {gc['hour']:+.1f} y día {gc['day']:+.1f} kWh.",
            "Cada barra suma o resta kWh al promedio; la cascada muestra cómo el modelo construye una predicción concreta paso a paso.",
            "Sirve para justificar ante el operador por qué el gemelo muestra ese consumo en un turno específico.",
        )


def render() -> None:
    st.header("7. Evaluación")
    m = read_json(pipeline.METRICS)
    if m is None:
        not_trained_message("La evaluación")
        train_all_button("btn_eval")
        return
    _metrics_section(m)
    _week_section()
    t, w = read_json(pipeline.MODEL_TESTS), read_json(pipeline.WINDOWS)
    if t and w:
        _tests_section(t, w)
    e = read_json(pipeline.EXPLAIN)
    if e:
        _explain_section(e, m)
    st.subheader("Modelo a exportar")
    exported = m["exported"]
    st.success(f"Modelo exportado: {exported} (menor MAE en el examen: {m['per_model'][exported]['mae']:.2f} kWh).")
    reading(
        f"{exported} obtiene el menor MAE del examen ({m['per_model'][exported]['mae']:.2f} kWh); los tres modelos se entrenaron con los mismos datos y la misma semilla.",
        "La regla de decisión es el MAE del último trimestre, que no participó en el ajuste; las pruebas de Friedman y Diebold-Mariano indican si "
        "la ventaja es sólida o pequeña.",
        "Ese modelo alimenta la tabla del artefacto que lee el gemelo; la pantalla Despliegue permite probar escenarios y descargar el JSON.",
    )
    train_all_button("btn_eval")
