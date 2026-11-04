# langchain-service

Small FastAPI service. Works with no LLM; an LLM is used only when `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set (and `pip install -r requirements-llm.txt`).

- `POST /query {"question": ...}`: answers over AGGREGATED results only. It calls the backend `GET /dashboard/summary`, whitelists aggregate fields (`app/facts.py`) and either returns a templated answer or, with an LLM key, asks the LLM using those facts only. No images, ids or pseudonyms are ever forwarded.
- `POST /rag {"question": ...}`: BM25 retrieval over `docs/*.md` (no embeddings). Returns sources, or "Insufficient evidence..." when retrieval score or term coverage is low. The docs are PLACEHOLDERS to be replaced by authorized documents.
- `langflow/tb_rag_flow.json`: hand-written prototype skeleton of the same RAG flow (re-save from Langflow after import).

```bash
pip install -r requirements.txt
TB_API_URL=http://localhost:8000 TB_API_TOKEN=<service token> uvicorn app.main:app --port 8100
pytest -q
```

Env: `TB_API_URL`, `TB_API_TOKEN` (from `python -m app.service_token` in `backend/`), optional `LC_SERVICE_KEY` (callers then send `X-API-Key`), optional LLM key.
