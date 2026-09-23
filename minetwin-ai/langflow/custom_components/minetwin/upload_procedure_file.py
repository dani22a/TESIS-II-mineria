from langflow.custom import Component
from langflow.io import FileInput, Output
from langflow.schema import Message

import csv
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


def _initialize(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS procedimientos (
            codigo TEXT PRIMARY KEY,
            dominio TEXT NOT NULL,
            titulo TEXT NOT NULL,
            regla TEXT NOT NULL
        );
        """
    )


def _resolve_csv_path(value) -> str:
    if value is None:
        raise ValueError("Falta el archivo CSV")
    if isinstance(value, list):
        value = value[0]
    if hasattr(value, "path"):
        return str(value.path)
    return str(value)


REQUIRED_COLUMNS = ("codigo", "dominio", "titulo", "regla")


class UploadProcedureFile(Component):
    display_name = "Upload Procedure File"
    description = "Carga un CSV de procedimientos operativos (codigo,dominio,titulo,regla) en Postgres."
    icon = "file-up"
    name = "UploadProcedureFile"

    inputs = [
        FileInput(
            name="csv_file",
            display_name="Archivo CSV",
            info="CSV con columnas: codigo, dominio, titulo, regla",
            file_types=["csv"],
        ),
    ]
    outputs = [
        Output(display_name="Resultado", name="output", method="load_procedures_into_database"),
    ]

    def load_procedures_into_database(self) -> Message:
        try:
            cursor = _connect()
            _initialize(cursor)
            path = _resolve_csv_path(self.csv_file)
            with open(path, "rt", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            if not rows:
                return Message(text="Error: CSV vacío")
            headers = {key.strip().lower() for key in rows[0].keys() if key}
            missing = [column for column in REQUIRED_COLUMNS if column not in headers]
            if missing:
                return Message(text=f"Error: faltan columnas {', '.join(missing)}")
            upserted = 0
            for row in rows:
                normalized = {str(k).strip().lower(): (v or "").strip() for k, v in row.items() if k}
                if not normalized.get("codigo") or not normalized.get("regla"):
                    continue
                cursor.execute(
                    """
                    INSERT INTO procedimientos (codigo, dominio, titulo, regla)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (codigo) DO UPDATE
                    SET dominio = EXCLUDED.dominio, titulo = EXCLUDED.titulo, regla = EXCLUDED.regla;
                    """,
                    (
                        normalized["codigo"],
                        normalized.get("dominio", "GENERAL").upper(),
                        normalized.get("titulo", normalized["codigo"]),
                        normalized["regla"],
                    ),
                )
                upserted += 1
            text = f"Correcto: {upserted} procedimientos cargados"
        except Exception as exc:
            text = f"Error: {exc}"
        self.status = text
        return Message(text=text)
