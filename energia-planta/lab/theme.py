"""Shared look: Plotly template, display labels and the small CSS injected by the app. Edit colors here."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from .config import LOAD_COLORS, LOAD_SHORT, MODEL_COLORS  # re-exported for convenience  # noqa: F401

INK = "#1F2430"
MUTED = "#5B6472"
GRID = "#E3E6EE"
ACCENT = "#4B4FD8"
NEUTRAL = "#9AA3B2"      # context series (e.g. raw 15-min data behind a daily mean)
POSITIVE = "#C8453F"     # pushes consumption up (SHAP, coefficients)
NEGATIVE = "#2E86AB"     # pushes consumption down
FONT = "Source Sans Pro, Segoe UI, Helvetica, Arial, sans-serif"

# Raw CSV column -> label shown to the user (display only; never used in the JSON or model inputs).
COLUMN_ES = {
    "Usage_kWh": "Consumo (kWh / 15 min)",
    "Lagging_Current_Reactive.Power_kVarh": "Potencia reactiva inductiva (kVarh)",
    "Leading_Current_Reactive_Power_kVarh": "Potencia reactiva capacitiva (kVarh)",
    "Lagging_Current_Power_Factor": "Factor de potencia inductivo (%)",
    "Leading_Current_Power_Factor": "Factor de potencia capacitivo (%)",
    "CO2(tCO2)": "CO2 (tCO2)",
    "NSM": "Segundos desde medianoche (NSM)",
    "WeekStatus": "Tipo de día (laborable o fin de semana)",
    "Day_of_week": "Día de la semana",
    "Load_Type": "Tipo de carga",
    "date": "Fecha y hora de fin del intervalo",
}
# Compact versions for heatmap axes and narrow tables.
COLUMN_SHORT = {
    "Usage_kWh": "Consumo",
    "Lagging_Current_Reactive.Power_kVarh": "Reactiva inductiva",
    "Leading_Current_Reactive_Power_kVarh": "Reactiva capacitiva",
    "Lagging_Current_Power_Factor": "F. de potencia inductivo",
    "Leading_Current_Power_Factor": "F. de potencia capacitivo",
    "CO2(tCO2)": "CO2",
    "NSM": "Seg. desde medianoche",
}
DTYPE_ES = {"float64": "decimal", "int64": "entero", "object": "texto", "str": "texto"}

_DAY_ES = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves",
           "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}
_LOAD_ES = {"Light_Load": "Ligera", "Medium_Load": "Media", "Maximum_Load": "Máxima"}


def feature_label(name: str) -> str:
    """Readable name of a model column (hour_sin, day_Monday, load_type_Light_Load...)."""
    if name == "hour_sin":
        return "Hora (seno)"
    if name == "hour_cos":
        return "Hora (coseno)"
    if name.startswith("day_"):
        return f"Día: {_DAY_ES.get(name[4:], name[4:])}"
    if name.startswith("load_type_"):
        return f"Carga: {_LOAD_ES.get(name[10:], name[10:])}"
    return COLUMN_ES.get(name, name)


def _build_template() -> go.layout.Template:
    t = go.layout.Template()
    t.layout = go.Layout(
        font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=[ACCENT, LOAD_COLORS["Medium_Load"], MODEL_COLORS["Random Forest"], LOAD_COLORS["Maximum_Load"], NEUTRAL],
        title=dict(font=dict(size=16, color=INK), x=0, xanchor="left", y=0.96, yanchor="top"),
        xaxis=dict(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID, ticks="outside", tickcolor=GRID,
                   title=dict(font=dict(size=12, color=MUTED)), automargin=True),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID,
                   title=dict(font=dict(size=12, color=MUTED)), automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text=""),
        hoverlabel=dict(font=dict(family=FONT, size=13), bgcolor="white", bordercolor=GRID),
        margin=dict(l=8, r=8, t=88, b=8),
    )
    return t


pio.templates["minetwin"] = _build_template()
TEMPLATE = "minetwin"


def style_fig(fig: go.Figure, title: str, *, x: str | None = None, y: str | None = None, height: int = 380,
              legend: bool = True, hover: str = ",.2f") -> go.Figure:
    """Apply the shared template, a subject title, Spanish axis titles (with units) and a hover format."""
    fig.update_layout(template=TEMPLATE, title_text=title, height=height, showlegend=legend)
    if x is not None:
        fig.update_xaxes(title_text=x)
    if y is not None:
        fig.update_yaxes(title_text=y, hoverformat=hover)
    return fig


# Small shared CSS: metric cards, reading callout and sidebar spacing. Native components do the rest.
CSS = """
<style>
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px; }
h1 { font-size: 2rem !important; letter-spacing: -0.01em; }
h2, h3 { letter-spacing: -0.005em; }
[data-testid="stMetricValue"], [data-testid="stDataFrame"] { font-variant-numeric: tabular-nums; }
[data-testid="stMetricLabel"] p { font-weight: 600; color: #5B6472; }
[class*="st-key-reading"] { background: #F3F4F9; border-radius: 0.6rem; padding: 0.25rem 0.5rem; }
[class*="st-key-reading"] p { margin-bottom: 0.15rem; }
[class*="st-key-winner"] { background: #EEF0FD; border-radius: 0.6rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label p { font-weight: 600; }
[data-testid="stSidebar"] [data-testid="stRadio"] label + div p, [data-testid="stSidebar"] small { color: #5B6472; }
</style>
"""
