"""EDA figures. Each builder returns (figure, (see, meaning, decision)) with numbers computed from the data."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

from .config import DAYS, DAYS_ES, LOAD_COLORS, LOAD_ES, LOAD_SHORT, LOAD_TYPES, TARGET
from .theme import ACCENT, COLUMN_SHORT, NEUTRAL, POSITIVE, TEMPLATE, style_fig

MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
_TPL = TEMPLATE


def figure_series(df: pd.DataFrame):
    """Full-year 15-min series with the daily mean."""
    d = df.sort_values("ts_start")
    daily = d.set_index("ts_start")[TARGET].resample("D").mean()
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=d["ts_start"], y=d[TARGET], mode="lines", name="Cada 15 min",
                               line=dict(width=0.6, color=NEUTRAL)))
    fig.add_trace(go.Scatter(x=daily.index, y=daily.values, mode="lines", name="Media diaria",
                             line=dict(width=2, color=ACCENT)))
    style_fig(fig, "Consumo de la planta durante el año completo", x="Fecha", y="Consumo (kWh / 15 min)")
    fig.update_layout(hovermode="x unified")

    monthly = d.groupby("month")[TARGET].mean()
    hi, lo = monthly.idxmax(), monthly.idxmin()
    low_share = float((d[TARGET] < 5).mean() * 100)
    see = (
        f"El consumo medio del año es {d[TARGET].mean():.1f} kWh por 15 min con picos de {d[TARGET].max():.0f} kWh. "
        f"El mes de mayor promedio es {MONTHS_ES[hi - 1]} ({monthly[hi]:.1f} kWh) y el menor {MONTHS_ES[lo - 1]} "
        f"({monthly[lo]:.1f} kWh); el {low_share:.0f} % de los registros está por debajo de 5 kWh."
    )
    meaning = (
        "La serie alterna un régimen de base bajo (planta ligera o detenida) con turnos de alta demanda, y el nivel "
        "medio cambia de mes a mes, es decir, no se mantiene estable durante el año."
    )
    decision = (
        "Un modelo que solo conozca hora, día y tipo de carga capturará el patrón de turnos pero no la deriva mensual: "
        "conviene validar hacia adelante en el tiempo y vigilar el error del último trimestre."
    )
    return fig, (see, meaning, decision)


def figure_profile(df: pd.DataFrame):
    """Mean consumption by start hour, one line per load type."""
    prof = df.groupby(["hour", "Load_Type"])[TARGET].mean().reset_index()
    fig = go.Figure()
    for lt in LOAD_TYPES:
        p = prof[prof["Load_Type"] == lt]
        fig.add_trace(go.Scatter(x=p["hour"], y=p[TARGET], mode="lines+markers", name=LOAD_SHORT[lt],
                                 line=dict(color=LOAD_COLORS[lt])))
    overall = df.groupby("hour")[TARGET].mean()
    fig.add_trace(go.Scatter(x=overall.index, y=overall.values, mode="lines", name="Todas las cargas",
                             line=dict(color="#444", dash="dot")))
    style_fig(fig, "Consumo medio por hora del día, según el tipo de carga",
              x="Hora del día (inicio del intervalo)", y="Consumo medio (kWh / 15 min)")
    fig.update_xaxes(dtick=2)
    fig.update_layout(hovermode="x unified")

    night = overall.loc[[2, 3, 4, 5]].mean()
    work = overall.loc[8:11].mean()
    dip_hour = int(overall.loc[11:14].idxmin())
    span = {lt: (prof[prof["Load_Type"] == lt].sort_values("hour")["hour"].agg(["min", "max"])).tolist() for lt in LOAD_TYPES}
    see = (
        f"La madrugada (02h a 05h) promedia {night:.1f} kWh y la mañana (08h a 11h) {work:.1f} kWh. Hay una caída marcada "
        f"a las {dip_hour:02d}h ({overall[dip_hour]:.1f} kWh). La carga máxima aparece entre las {span['Maximum_Load'][0]:02d}h "
        f"y las {span['Maximum_Load'][1]:02d}h y la ligera durante todo el día."
    )
    meaning = (
        "El consumo sigue un horario de turnos, con una parada a mediodía y un tramo de tarde-noche más bajo; el tipo de "
        "carga se concentra en ciertas horas, por lo que hora y carga están relacionadas, y dentro de cada carga la "
        "hora aún modifica el nivel."
    )
    decision = (
        "Los turnos de alta demanda son predecibles con el reloj: se pueden programar cargas flexibles fuera de las "
        "horas pico y esperar la caída del mediodía como referencia de planta detenida."
    )
    return fig, (see, meaning, decision)


def figure_box_day(df: pd.DataFrame):
    d = df.copy()
    d["Día"] = d["day"].map(DAYS_ES)
    fig = px.box(d, x="Día", y=TARGET, category_orders={"Día": [DAYS_ES[x] for x in DAYS]}, template=_TPL,
                 color_discrete_sequence=[ACCENT], points=False)
    style_fig(fig, "Distribución del consumo según el día de la semana", x="Día de la semana",
              y="Consumo (kWh / 15 min)", legend=False)
    med = d.groupby("day")[TARGET].median().reindex(DAYS)
    mean = d.groupby("day")[TARGET].mean().reindex(DAYS)
    wk = mean[["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]]
    see = (
        "Medias por día: " + ", ".join(f"{DAYS_ES[k][:3]} {v:.1f}" for k, v in mean.items())
        + f" kWh. Entre lunes y viernes la media va de {wk.min():.1f} a {wk.max():.1f} kWh y el domingo cae a {mean['Sunday']:.1f} kWh. "
        "Las medianas (de 3 a 20 kWh) son inestables porque la distribución diaria tiene dos regímenes, base y turno."
    )
    meaning = (
        "De lunes a viernes la distribución es casi la misma; el sábado baja y el domingo cae con fuerza, con "
        "muchos registros cercanos al consumo de base."
    )
    decision = (
        "El día de la semana debe entrar al modelo; en el gemelo, el fin de semana es el momento de menor demanda "
        "eléctrica y el mejor candidato para mantenimiento o para consumo mínimo."
    )
    return fig, (see, meaning, decision)


def figure_box_load(df: pd.DataFrame):
    d = df.copy()
    d["Tipo de carga"] = d["Load_Type"].map(LOAD_SHORT)
    fig = px.box(d, x="Tipo de carga", y=TARGET, color="Load_Type", color_discrete_map=LOAD_COLORS,
                 category_orders={"Tipo de carga": [LOAD_SHORT[t] for t in LOAD_TYPES]}, template=_TPL, points=False)
    style_fig(fig, "Distribución del consumo según el tipo de carga", x="Tipo de carga",
              y="Consumo (kWh / 15 min)", legend=False)
    q = d.groupby("Load_Type")[TARGET].quantile([0.25, 0.5, 0.75]).unstack().reindex(LOAD_TYPES)
    see = "; ".join(
        f"{LOAD_ES[t].lower()}: mediana {q.loc[t, 0.5]:.1f} kWh (rango intercuartil {q.loc[t, 0.25]:.1f} a {q.loc[t, 0.75]:.1f})"
        for t in LOAD_TYPES
    ) + "."
    meaning = (
        "Las cargas se ordenan de menor a mayor consumo, pero la carga media tiene una caja muy ancha que abarca desde "
        "valores de base hasta niveles altos, y la carga ligera tiene valores atípicos altos: el tipo de carga solo "
        "no basta para fijar el kWh."
    )
    decision = (
        "Combinar el tipo de carga con la hora reduce la incertidumbre; el operador no debe asumir un consumo fijo "
        "por régimen, sino un rango según el turno."
    )
    return fig, (see, meaning, decision)


def figure_spearman(matrix: pd.DataFrame):
    labels = [COLUMN_SHORT.get(c, c) for c in matrix.columns]
    fig = go.Figure(go.Heatmap(z=matrix.values, x=labels, y=labels, zmin=-1, zmax=1, colorscale="RdBu_r",
                               text=np.round(matrix.values, 2), texttemplate="%{text}",
                               colorbar=dict(title="Correlación"),
                               hovertemplate="%{y} y %{x}: %{z:.2f}<extra></extra>"))
    style_fig(fig, "Correlación de Spearman entre las variables del archivo", height=500, legend=False)
    fig.update_layout(margin=dict(t=64))
    fig.update_yaxes(autorange="reversed")
    r = matrix[TARGET].drop(TARGET).sort_values(key=lambda s: -s.abs())
    top = ", ".join(f"{COLUMN_SHORT.get(k, k).lower()} ({v:.2f})" for k, v in r.head(3).items())
    see = f"Las mayores correlaciones de Spearman con el consumo son: {top}. NSM y factor de potencia leading quedan por debajo de 0.4."
    meaning = (
        "El CO2 sigue al consumo casi peso a peso y la reactiva lagging lo acompaña; ambas son consecuencia de operar "
        "la carga, no causas que el gemelo pueda fijar de antemano."
    )
    decision = (
        "Reactiva y factor de potencia sirven para diagnosticar la calidad de la energía, pero no son entradas "
        "del pronóstico; el CO2 se calcula a partir del kWh predicho."
    )
    return fig, (see, meaning, decision)


def figure_co2(df: pd.DataFrame):
    """CO2 vs consumption: scatter plus a week of standardized series."""
    co2 = "CO2(tCO2)"
    rs = df[[TARGET, co2]].sample(6000, random_state=42)
    slope, intercept, r, _, _ = stats.linregress(df[TARGET], df[co2])
    d = df.sort_values("ts_start")
    week = d[(d["ts_start"] >= "2018-03-05") & (d["ts_start"] < "2018-03-12")]
    z = lambda s: (s - s.mean()) / s.std()
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Consumo frente a CO2 (6,000 registros)", "Una semana, ambas series estandarizadas"))
    fig.add_trace(go.Scattergl(x=rs[TARGET], y=rs[co2], mode="markers", marker=dict(size=4, opacity=0.35, color=NEUTRAL),
                               name="Registros"), row=1, col=1)
    xs = np.array([0, df[TARGET].max()])
    fig.add_trace(go.Scatter(x=xs, y=intercept + slope * xs, mode="lines", line=dict(color=POSITIVE), name="Recta ajustada"), row=1, col=1)
    fig.add_trace(go.Scatter(x=week["ts_start"], y=z(week[TARGET]), mode="lines", name="Consumo (estandarizado)", line=dict(color=ACCENT)), row=1, col=2)
    fig.add_trace(go.Scatter(x=week["ts_start"], y=z(week[co2]), mode="lines", name="CO2 (estandarizado)", line=dict(color=POSITIVE, dash="dot")), row=1, col=2)
    style_fig(fig, "El CO2 reproduce al consumo", height=420)
    fig.update_xaxes(title_text="Consumo (kWh / 15 min)", row=1, col=1)
    fig.update_yaxes(title_text="CO2 (tCO2 / 15 min)", row=1, col=1)
    fig.update_xaxes(title_text="Fecha", row=1, col=2)
    fig.update_yaxes(title_text="Desviaciones estándar", row=1, col=2)

    n_levels = df[co2].nunique()
    ratio = df[co2].sum() / df[TARGET].sum()
    see = (
        f"La correlación de Pearson entre CO2 y kWh es {r:.3f} (R² = {r ** 2:.3f}). El factor global es {ratio:.6f} tCO2 por kWh "
        f"(unos {ratio * 1000:.2f} kg por kWh) y el CO2 solo toma {n_levels} valores distintos porque está redondeado a 0.01 t."
    )
    meaning = (
        "El CO2 no aporta información propia: es el consumo multiplicado por un factor y redondeado. Meterlo como "
        "variable explicativa filtraría la respuesta al modelo."
    )
    decision = (
        "Se excluye del modelo y se calcula después desde los kWh pronosticados; en el gemelo, el reporte de emisiones "
        "sale de multiplicar el kWh por el factor, sin otro sensor."
    )
    return fig, (see, meaning, decision)
