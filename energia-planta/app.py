"""MineTwin energy lab: Streamlit app organised by CRISP-DM phases."""
import importlib

import streamlit as st

from lab.config import PHASES
from lab.ui import inject_css, render_sidebar

st.set_page_config(page_title="Laboratorio de energía de planta", page_icon=":material/bolt:", layout="wide")

# Screen modules by phase; a phase whose module is not implemented yet is shown as pending.
SCREENS = dict(zip(PHASES, (
    "screens.negocio", "screens.datos", "screens.eda", "screens.pruebas",
    "screens.preparacion", "screens.modelado", "screens.evaluacion", "screens.despliegue",
)))


def main() -> None:
    inject_css()
    phase = render_sidebar()

    try:
        module = importlib.import_module(SCREENS[phase])
    except ModuleNotFoundError as exc:
        if exc.name != SCREENS[phase]:
            raise
        st.title(phase)
        st.info("Esta fase aún no está implementada.")
        return
    module.render()


main()
