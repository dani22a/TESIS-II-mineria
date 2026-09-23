from langflow.custom import Component
from langflow.io import DropdownInput, FileInput, Output, StrInput
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


def _normalize_language(value: str | None, default: str = "en") -> str:
    if not value:
        return default
    key = str(value).strip().lower()
    mapping = {
        "en": "en",
        "es": "es",
        "zh": "zh",
        "english": "en",
        "spanish": "es",
        "chinese": "zh",
        "ingles": "en",
        "español": "es",
        "espanol": "es",
        "chino": "zh",
        "中文": "zh",
        "英语": "en",
        "西班牙语": "es",
    }
    return mapping.get(key, default)


def _initialize(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS words (
            word TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'en',
            PRIMARY KEY (word, language)
        );
        """
    )


def _add_word(cursor, word: str, language: str) -> None:
    cleaned = (word or "").strip()
    if not cleaned:
        return
    cursor.execute(
        """
        INSERT INTO words (word, language)
        VALUES (%s, %s)
        ON CONFLICT (word, language) DO NOTHING;
        """,
        (cleaned, language),
    )


def _resolve_csv_path(value) -> str:
    if value is None:
        raise ValueError("CSV file is required")
    if isinstance(value, list):
        value = value[0]
    if hasattr(value, "path"):
        return str(value.path)
    return str(value)


class UploadWordFile(Component):
    display_name = "Upload Word File"
    description = "Upload a CSV of known words into the vocabulary database (English, Spanish, Chinese)."
    icon = "file-up"
    name = "UploadWordFile"

    inputs = [
        StrInput(
            name="column_name",
            display_name="Column Name",
            info="The name of the column containing the words",
            value="word",
        ),
        StrInput(
            name="language_column",
            display_name="Language Column",
            info="Optional CSV column with language codes: en, es, zh",
            value="language",
        ),
        DropdownInput(
            name="default_language",
            display_name="Default Language",
            options=["en", "es", "zh"],
            value="en",
            info="Used when the CSV has no language column",
        ),
        FileInput(
            name="csv_file",
            display_name="CSV file",
            info="CSV input file",
            file_types=["csv"],
        ),
    ]
    outputs = [
        Output(display_name="Output", name="output", method="load_words_into_database"),
    ]

    def load_words_into_database(self) -> Message:
        try:
            cursor = _connect()
            _initialize(cursor)
            path = _resolve_csv_path(self.csv_file)
            with open(path, "rt", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
            if not rows:
                return Message(text="Error: empty CSV")
            headers = [header.strip().lower() for header in rows[0]]
            column_index = headers.index(str(self.column_name).strip().lower())
            language_index = None
            language_column = (self.language_column or "").strip().lower()
            if language_column and language_column in headers:
                language_index = headers.index(language_column)
            inserted = 0
            for row in rows[1:]:
                if not row or column_index >= len(row):
                    continue
                language = self.default_language
                if language_index is not None and language_index < len(row):
                    language = row[language_index]
                _add_word(cursor, row[column_index], _normalize_language(language, self.default_language))
                inserted += 1
            text = f"Success: loaded {inserted} words"
            self.status = text
            return Message(text=text)
        except Exception as exc:
            text = f"Error: {exc}"
            self.status = text
            return Message(text=text)
