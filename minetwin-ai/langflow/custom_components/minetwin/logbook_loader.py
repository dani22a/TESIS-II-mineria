from langflow.custom import Component
from langflow.io import IntInput, Output
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


class LogbookLoader(Component):
    display_name = "Logbook Loader"
    description = "Carga los últimos eventos de la bitácora de turno desde Postgres."
    icon = "notebook-text"
    name = "LogbookLoader"

    inputs = [
        IntInput(
            name="limit",
            display_name="Cantidad de eventos",
            info="Número máximo de eventos recientes a cargar.",
            value=20,
        ),
    ]
    outputs = [
        Output(display_name="Bitácora", name="output", method="build_output"),
    ]

    def build_output(self) -> Message:
        try:
            cursor = _connect()
            limit = int(getattr(self, "limit", 20) or 20)
            cursor.execute(
                """
                SELECT id, to_char(creado_en, 'YYYY-MM-DD HH24:MI'), categoria, COALESCE(activo, '-'), descripcion, autor
                FROM bitacora_turno
                ORDER BY creado_en DESC, id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = list(reversed(cursor.fetchall()))
            if not rows:
                text = "(bitácora vacía)"
            else:
                text = "\n".join(
                    f"- #{row_id} {fecha} [{categoria}] activo={activo}: {descripcion} ({autor})"
                    for row_id, fecha, categoria, activo, descripcion, autor in rows
                )
        except Exception as exc:
            text = f"(no se pudo cargar la bitácora: {exc})"
        self.status = text
        return Message(text=text)
