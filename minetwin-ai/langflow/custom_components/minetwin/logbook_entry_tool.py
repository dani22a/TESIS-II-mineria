from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Message

import json
import os
import urllib.request


def _session_id(component) -> str | None:
    try:
        return component.graph.session_id
    except Exception:
        return None


def _report_trace(session_id: str | None, result: dict) -> None:
    # Informa la escritura a MineTwin solo para mostrarla en la línea de tiempo; si falla no afecta el registro.
    configured = [url.strip().rstrip("/") for url in os.getenv("MINETWIN_API_URL", "").split(",") if url.strip()]
    body = json.dumps(
        {
            "session_id": session_id,
            "tool": "registrar_evento_bitacora",
            "citation": "Postgres bitacora_turno (Langflow)",
            "result": result,
        }
    ).encode("utf-8")
    for base in configured:
        try:
            request = urllib.request.Request(
                f"{base}/api/twin/trace", data=body, method="POST", headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(request, timeout=5):
                return
        except Exception:
            continue


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


CATEGORIES = {"OBSERVACION", "INCIDENTE", "MANTENCION", "CLIMA", "DECISION_HITL", "INICIO_TURNO", "FIN_TURNO"}


class LogbookEntryTool(Component):
    display_name = "Registrar en bitácora"
    description = (
        "Registra un evento en la bitácora de turno de la mina (Postgres). Úsala cuando el usuario pida "
        "anotar, registrar o dejar constancia de un evento, incidente, cambio de clima o decisión de aprobación."
    )
    icon = "notebook-pen"
    name = "LogbookEntryTool"

    inputs = [
        MessageTextInput(
            name="descripcion",
            display_name="Descripción",
            info="Texto del evento a registrar, en español.",
            tool_mode=True,
        ),
        MessageTextInput(
            name="categoria",
            display_name="Categoría",
            info="Una de: OBSERVACION, INCIDENTE, MANTENCION, CLIMA, DECISION_HITL, INICIO_TURNO, FIN_TURNO.",
            tool_mode=True,
            value="OBSERVACION",
        ),
        MessageTextInput(
            name="activo",
            display_name="Activo",
            info="Opcional: ID del equipo involucrado, ej. EX-02, DT-03, CR-01.",
            tool_mode=True,
            value="",
        ),
    ]
    outputs = [
        Output(display_name="Resultado", name="output", method="registrar_evento_bitacora"),
    ]

    def registrar_evento_bitacora(self) -> Message:
        descripcion = str(self.descripcion or "").strip()
        if not descripcion:
            return Message(text="Error: la descripción del evento está vacía.")
        categoria = str(self.categoria or "OBSERVACION").strip().upper()
        if categoria not in CATEGORIES:
            categoria = "OBSERVACION"
        activo = str(self.activo or "").strip().upper() or None
        try:
            cursor = _connect()
            cursor.execute(
                """
                INSERT INTO bitacora_turno (categoria, activo, descripcion, autor)
                VALUES (%s, %s, %s, 'copiloto-langflow')
                RETURNING id;
                """,
                (categoria, activo, descripcion),
            )
            entry_id = cursor.fetchone()[0]
            text = f"Evento #{entry_id} registrado en bitácora [{categoria}] {activo or ''}: {descripcion}".strip()
            _report_trace(
                _session_id(self),
                {"id": entry_id, "categoria": categoria, "activo": activo, "descripcion": descripcion},
            )
        except Exception as exc:
            text = f"Error al registrar en bitácora: {exc}"
        self.status = text
        return Message(text=text)
