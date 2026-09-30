"""Streamlit helpers: shared page skeleton, readings, sidebar, cached loaders and artifact I/O."""
from __future__ import annotations

import json
import zlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import config
from . import data as data_mod
from .config import ARTIFACTS, DATA_PATH, PHASE_META
from .glossary import GLOSSARY, help_text
from .theme import CSS

__all__ = ["help_text"]

N_PHASES = len(PHASE_META)


# ---------------------------------------------------------------- number formatting (one style)
# Decimal point, thousands comma, unit after a space: "11.49 kWh", "35,040".
def fmt(x: float, digits: int = 1) -> str:
    return f"{x:,.{digits}f}"


def fmt_kwh(x: float, digits: int = 2) -> str:
    return f"{x:,.{digits}f} kWh"


def fmt_p(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


# ---------------------------------------------------------------- building blocks
def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def show_fig(fig: go.Figure) -> None:
    """Render a Plotly figure keeping the shared template (Streamlit's own theme is turned off)."""
    st.plotly_chart(fig, theme=None, width="stretch", config={"displaylogo": False})


def reading(see: str, meaning: str, decision: str) -> None:
    """The three fixed lines shown under every figure and table, as one scannable callout."""
    rows = [
        (":material/visibility:", "Qué se ve", see),
        (":material/lightbulb:", "Qué significa", meaning),
        (":material/engineering:", "Qué decisión permite en la planta", decision),
    ]
    key = f"reading_{zlib.crc32(see.encode('utf-8')):x}"
    with st.container(border=True, key=key):
        for icon, label, text in rows:
            c1, c2 = st.columns([2, 7], vertical_alignment="top")
            c1.markdown(f"{icon} **{label}**")
            c2.markdown(text)


def glossary_expander(terms: list[str] | None = None, label: str = "Glosario: qué significa cada término") -> None:
    """Expander listing glossary terms (all of them when `terms` is None)."""
    with st.expander(label, icon=":material/menu_book:"):
        for term in terms or list(GLOSSARY):
            name, text = GLOSSARY[term]
            st.markdown(f"**{term}** ({name}). {text}" if name != term else f"**{term}.** {text}")


def page_header(n: int, purpose: str, kpis: list[tuple] | None = None) -> None:
    """Common top of every screen: numbered title, purpose sentence and 3-4 headline KPI cards.

    kpis: (label, value) or (label, value, help) tuples.
    """
    meta = PHASE_META[n - 1]
    st.title(f"Fase {n} de {N_PHASES}: {meta['title']}")
    st.markdown(f"**Para qué sirve esta pantalla.** {purpose}")
    if kpis:
        for col, k in zip(st.columns(len(kpis)), kpis):
            col.metric(k[0], k[1], help=k[2] if len(k) > 2 else None, border=True)


def _go_to(key: str) -> None:
    st.session_state["fase"] = key


def next_step(n: int) -> None:
    """Closing hint pointing at the next phase, with a button that navigates there."""
    st.divider()
    if n >= N_PHASES:
        st.markdown("**Siguiente paso.** Ciclo completo: el gemelo digital lee el artefacto descargado; "
                    "para repetir el ciclo con datos nuevos se vuelve a la fase 1 o se reentrena aquí.")
        st.button("Volver a la fase 1 · Negocio", on_click=_go_to, args=(PHASE_META[0]["key"],), key="next_8")
        return
    nxt = PHASE_META[n]
    st.markdown(f"**Siguiente paso.** {PHASE_META[n - 1]['next']}")
    st.button(f"Ir a la fase {nxt['label']}", icon=":material/arrow_forward:", on_click=_go_to, args=(nxt["key"],),
              key=f"next_{n}")


# ---------------------------------------------------------------- sidebar
def pipeline_status() -> list[tuple[str, bool, str, str]]:
    """(label, ok, text if ok, text if missing) for the sidebar status block."""
    return [
        ("Datos", DATA_PATH.exists(), "archivo encontrado", "falta data/Steel_industry_data.csv"),
        ("Modelo", (ARTIFACTS / "metricas_examen.json").exists(), "entrenado", "sin entrenar"),
        ("Artefacto", config.FINAL_ARTIFACT.exists(), "exportado", "sin exportar"),
    ]


def render_sidebar() -> str:
    """Product title, numbered phase stepper with captions, status block and glossary. Returns the phase key."""
    sb = st.sidebar
    sb.title("Energía de planta")
    sb.caption("Laboratorio que predice cuántos kWh consume la planta cada 15 minutos y compara tres modelos.")
    labels = {m["key"]: m["label"] for m in PHASE_META}
    phase = sb.radio("Fases del proyecto (CRISP-DM)", list(labels), key="fase", format_func=labels.get,
                     captions=[m["subtitle"] for m in PHASE_META])
    n = list(labels).index(phase) + 1
    sb.progress(n / N_PHASES, text=f"Está en la fase {n} de {N_PHASES}")

    sb.markdown("**Estado del proyecto**")
    for name, ok, yes, no in pipeline_status():
        sb.markdown(f":green[:material/check_circle:] {name}: {yes}" if ok
                    else f":orange[:material/error:] {name}: {no}")
    sb.caption("El signo de interrogación junto a un dato explica qué significa.")
    with sb.expander("Glosario", icon=":material/menu_book:"):
        for term in GLOSSARY:
            _, text = GLOSSARY[term]
            st.markdown(f"**{term}.** {text}")
    sb.caption(f"Semilla fija: {config.SEED}")
    return phase


# ---------------------------------------------------------------- data and artifacts
def data_available() -> bool:
    return DATA_PATH.exists()


@st.cache_data(show_spinner="Cargando datos...")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (raw, prepared) frames; cached across reruns."""
    raw = data_mod.load_raw()
    return raw, data_mod.prepare(raw)


@st.cache_data(show_spinner="Calculando reporte de calidad...")
def load_quality() -> dict:
    raw, df = load_data()
    return data_mod.quality_report(raw, df)


def missing_data_banner() -> None:
    st.error(
        "**No se encontró el archivo de datos.** Copie `Steel_industry_data.csv` en la carpeta `data/` "
        f"(ruta esperada: `{DATA_PATH}`; el archivo no se versiona) y recargue la página.",
        icon=":material/folder_off:",
    )


def require_data(n: int | None = None, purpose: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Load the data or show the friendly banner and return None. With n/purpose it also draws the page header."""
    if not data_available():
        if n is not None:
            page_header(n, purpose or "")
        missing_data_banner()
        return None
    return load_data()


def read_json(name: str):
    """Read a JSON artifact from artefactos/, or None when it does not exist."""
    path = ARTIFACTS / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def not_trained_message(what: str = "Esta pantalla", *, button: bool = True) -> None:
    """The single banner used whenever a screen needs results that do not exist yet."""
    how = ("Pulse el botón de abajo, o ejecute `python train.py` en la terminal"
           if button else "Ejecute `python train.py` en la terminal, o use el botón de entrenamiento de la fase 7 · Evaluación")
    st.warning(
        f"**{what} aún no tiene resultados porque el modelo no ha sido entrenado.** {how}; tarda un par de minutos.",
        icon=":material/hourglass_empty:",
    )


def train_all_button(key: str, *, expanded: bool = False) -> None:
    """'Entrenar / Re-entrenar' control that runs the same code as train.py (phases 5-8 end to end)."""
    with st.expander("Reentrenar el modelo y exportar el artefacto", icon=":material/model_training:", expanded=expanded):
        st.caption("Ejecuta el mismo código que `python train.py`: búsqueda de hiperparámetros, examen, explicabilidad y exportación.")
        reuse = st.checkbox("Reutilizar los hiperparámetros congelados (más rápido)", value=True, key=f"reuse_{key}")
        if st.button("Entrenar y exportar el artefacto", key=key, type="primary"):
            from . import pipeline  # lazy: pulls in xgboost and shap

            bar = st.progress(0.0)
            with st.spinner("Entrenando y exportando (puede tardar un par de minutos)..."):
                pipeline.run_all(progress=lambda msg, frac: bar.progress(min(frac, 1.0), text=msg), reuse_search=reuse)
            st.cache_data.clear()
            st.success("Entrenamiento terminado; artefactos actualizados.")
            st.rerun()
