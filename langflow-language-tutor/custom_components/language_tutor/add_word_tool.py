from langflow.custom import Component
from langflow.io import MessageTextInput, Output
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


class AddWordTool(Component):
    display_name = "Add word tool"
    description = "Use this tool to add a new word to the learner vocabulary. Include the word and its language (English, Spanish, or Chinese)."
    icon = "plus"
    name = "AddWordTool"

    inputs = [
        MessageTextInput(
            name="word",
            display_name="Word",
            info="The word to add",
            tool_mode=True,
        ),
        MessageTextInput(
            name="language",
            display_name="Language",
            info="Language of the word: English/en, Spanish/es, or Chinese/zh",
            tool_mode=True,
            value="en",
        ),
    ]
    outputs = [
        Output(display_name="Output", name="output", method="add_new_word"),
    ]

    def add_new_word(self) -> Message:
        cursor = _connect()
        language = _normalize_language(getattr(self, "language", None), "en")
        _add_word(cursor, self.word, language)
        labels = {"en": "English", "es": "Spanish", "zh": "Chinese"}
        text = f"Added word: {self.word} ({labels.get(language, language)})"
        self.status = text
        return Message(text=text)
