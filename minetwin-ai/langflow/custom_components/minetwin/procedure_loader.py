from langflow.custom import Component
from langflow.io import DropdownInput, Output
from langflow.schema import Message

import os


def _connect():
    params = dict(
        dbname=os.getenv("POSTGRES_DB", "langflow"),
        user=os.getenv("POSTGRES_USER", "langflow"),
        password=os.getenv("POSTGRES_PASSWORD", "langflow"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
    )
    try:
        import psycopg2

        conn = psycopg2.connect(**params)
        conn.autocommit = True
        return conn.cursor()
    except ImportError:
        import psycopg

        conn = psycopg.connect(**params, autocommit=True)
        return conn.cursor()


class ProcedureLoader(Component):
    display_name = "Procedure Loader"
    description = "Carga los procedimientos operativos (SOP) de la mina desde Postgres."
    icon = "book-open"
    name = "ProcedureLoader"

    inputs = [
        DropdownInput(
            name="domain",
            display_name="Dominio",
            options=["TODOS", "DESPACHO", "TRONADURA", "PLANTA", "SEGURIDAD", "REPORTE"],
            value="TODOS",
            info="Cargar todos los procedimientos o solo los de un dominio.",
        ),
    ]
    outputs = [
        Output(display_name="Procedimientos", name="output", method="build_output"),
    ]

    def build_output(self) -> Message:
        try:
            cursor = _connect()
            domain = str(getattr(self, "domain", "TODOS") or "TODOS").upper()
            if domain == "TODOS":
                cursor.execute("SELECT codigo, dominio, titulo, regla FROM procedimientos ORDER BY dominio, codigo;")
            else:
                cursor.execute(
                    "SELECT codigo, dominio, titulo, regla FROM procedimientos WHERE dominio = %s ORDER BY codigo;",
                    (domain,),
                )
            rows = cursor.fetchall()
            if not rows:
                text = "(sin procedimientos cargados)"
            else:
                text = "\n".join(f"- [{codigo}] ({dominio}) {titulo}: {regla}" for codigo, dominio, titulo, regla in rows)
        except Exception as exc:
            text = f"(no se pudieron cargar los procedimientos: {exc})"
        self.status = text
        return Message(text=text)
