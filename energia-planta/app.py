"""MineTwin energy lab: Streamlit app organised by CRISP-DM phases."""
import importlib

import streamlit as st

from lab.config import PHASES, SEED

st.set_page_config(page_title="Laboratorio de energía de planta", layout="wide")

# Screen modules by phase; a phase whose module is not implemented yet is shown as pending.
SCREENS = {
    "1. Negocio": "screens.negocio",
    "2. Datos": "screens.datos",
    "3. EDA": "screens.eda",
    "4. Pruebas": "screens.pruebas",
    "5. Preparación": "screens.preparacion",
    "6. Modelado": "screens.modelado",
    "7. Evaluación": "screens.evaluacion",
    "8. Despliegue": "screens.despliegue",
}


def main() -> None:
    st.sidebar.title("Energía de planta")
    st.sidebar.caption("CRISP-DM · Usage_kWh cada 15 min")
    phase = st.sidebar.radio("Fase", PHASES, key="fase")
    st.sidebar.markdown(f"Semilla fija: **{SEED}**")

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
