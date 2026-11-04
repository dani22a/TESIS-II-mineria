import os


def backend_url() -> str:
    return os.environ.get("TB_API_URL", "http://localhost:8000").rstrip("/")


def backend_token() -> str:
    return os.environ.get("TB_API_TOKEN", "")  # service token (python -m app.service_token)


def service_key() -> str:
    return os.environ.get("LC_SERVICE_KEY", "")  # if set, callers must send X-API-Key


def llm_provider() -> str | None:
    """'anthropic' / 'openai' only when the matching API key env var is set; else None (no LLM)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None
