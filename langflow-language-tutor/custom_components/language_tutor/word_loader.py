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


def _normalize_language(value: str | None) -> str | None:
    if not value or str(value).strip().lower() in {"all", "*", ""}:
        return None
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
    return mapping.get(key, key)


def _load_words(language: str | None):
    cursor = _connect()
    if language:
        cursor.execute(
            "SELECT word, language FROM words WHERE language = %s ORDER BY word;",
            (language,),
        )
    else:
        cursor.execute("SELECT word, language FROM words ORDER BY language, word;")
    return [(row[0], row[1]) for row in cursor.fetchall()]


def _format_words(rows) -> str:
    grouped = {"en": [], "es": [], "zh": []}
    for word, language in rows:
        grouped.setdefault(language, []).append(word)
    parts = []
    for code, label in (("en", "English"), ("es", "Spanish"), ("zh", "Chinese")):
        words = grouped.get(code) or []
        parts.append(f"{label}: {', '.join(words) if words else '(empty)'}")
    return "\n".join(parts)


class WordLoader(Component):
    display_name = "Word Loader"
    description = "Load known vocabulary from the database for English, Spanish, and Chinese."
    icon = "database"
    name = "WordLoader"

    inputs = [
        DropdownInput(
            name="language",
            display_name="Language",
            options=["all", "en", "es", "zh"],
            value="all",
            info="Load all languages or a single vocabulary list",
        ),
    ]
    outputs = [
        Output(display_name="Output", name="output", method="build_output"),
    ]

    def build_output(self) -> Message:
        language = _normalize_language(getattr(self, "language", "all"))
        rows = _load_words(language)
        if language:
            labels = {"en": "English", "es": "Spanish", "zh": "Chinese"}
            words = [word for word, _ in rows]
            text = f"{labels.get(language, language)}: {', '.join(words) if words else '(empty)'}"
        else:
            text = _format_words(rows)
        self.status = text
        return Message(text=text)
