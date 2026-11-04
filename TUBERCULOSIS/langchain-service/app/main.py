from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import config
from .facts import extract_facts, templated_answer
from .llm import answer_with_llm
from .rag import Retriever

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
app = FastAPI(title="TB screening LangChain service", version="0.1.0")
_retriever: Retriever | None = None


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


def check_key(x_api_key: str | None = Header(default=None)):
    key = config.service_key()
    if key and x_api_key != key:
        raise HTTPException(401, "Invalid API key")


def fetch_summary() -> dict:
    """Aggregate dashboard summary from the backend (dependency, overridable in tests)."""
    try:
        r = httpx.get(f"{config.backend_url()}/dashboard/summary", timeout=15,
                      headers={"Authorization": f"Bearer {config.backend_token()}"})
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Backend unavailable: {type(e).__name__}")


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(DOCS_DIR)
    return _retriever


@app.get("/health")
def health():
    return {"status": "ok", "llm": config.llm_provider() or "none (templated answers)"}


@app.post("/query", dependencies=[Depends(check_key)])
def query(body: Question, summary: dict = Depends(fetch_summary)):
    facts = extract_facts(summary)  # aggregates only
    llm = answer_with_llm(body.question, facts)
    return {"answer": llm or templated_answer(body.question, facts), "mode": "llm" if llm else "template",
            "is_demo": facts["is_demo"], "facts": facts}


@app.post("/rag", dependencies=[Depends(check_key)])
def rag(body: Question, r: Retriever = Depends(get_retriever)):
    return r.search(body.question)
