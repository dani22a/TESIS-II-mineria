# tb-screening

**Objective:** Implement SP-02 (assisted pulmonary TB screening from chest X-rays with explainable vision models) in `TUBERCULOSIS/`: FastAPI + React/TS + PostgreSQL web app, 6 n8n workflows, LangChain/LangFlow, and a reproducible ML experimental pipeline. Source: `TEMATICA-SP-02.docx` (in Downloads) + master prompt.
**Constraints:** Demo mode clearly flagged in UI/API/reports; no scientific metrics published unless computed on proper eval data. Roles: admin/operator/reviewer/auditor, enforced in API. Audit log append-only. LLM never sees images or patient ids; core flow works without an LLM. Docker is NOT installed locally: compose files are written but not run; local verification uses Postgres 18 (psql present), Python 3.12, Node 24.
**TDD:** suggestion-based (tests proposed, not written unilaterally; exception: the master prompt explicitly demands API permission/flow tests, so those are in scope as user-requested). **Checks:** pytest, `npm run build`, e2e smoke script.
**Delivery:** ask-on-risk; forecast far above 400 lines. Branch/commit target NOT yet decided by the user (asked; user only answered folder). No commits until answered.

## Tasks
- [x] T0 Scaffold `TUBERCULOSIS/`: docs/requisitos.md, docker-compose, .env.example, README skeleton. Route: delegated writer.
- [x] T1 Backend core: Alembic, auth/JWT, roles, cases, upload + QC, demo inference, review, audit log (module enter/exit, login/logout, exports). Route: delegated writer.
- [x] T2 Frontend: login, cases, upload, result + review, dashboard, audit log, module enter/exit tracking.
- [x] T3 Dashboard endpoints + reports PDF/DOCX/XLSX from one data source with same filters/permissions.
- [x] T4 n8n WF-01..06 (importable JSON), LangChain service (aggregate query + RAG), LangFlow export. Route: delegated writer. Evidence: backend pytest 38 passed (added `service` role, `/ops/*`, `app.service_token`, `tests/test_ops.py`); langchain-service pytest 3 passed; workflow JSON validated structurally only (no n8n available).
- [x] T5 ML pipeline: data prep, 5 models, group splits, Optuna, evaluation, Grad-CAM, stats tests, MLflow. Route: delegated writer. Evidence: ml pytest 13 passed; `python -m tbml.smoke` ran end to end on SYNTHETIC data (CPU torch 2.15); MLflow not installed (skipped gracefully); no real data used, no scientific claim.
- [x] T6 End-to-end verification of the golden path, README commands, final report. Route: delegated writer. Evidence: `scripts/e2e_smoke.py --spawn` (live uvicorn, SQLite) 26/26 checks; `npm run build` OK; vite preview + live backend curl-level CORS/API-base OK; backend pytest 38 passed; README completed.

## Progress / evidence
T0-T6 done (no commits yet; branch/commit target undecided). Checks observed: backend pytest 38, ml pytest 13, langchain-service pytest 3, `npm run build`, e2e smoke 26/26 on live server (SQLite), CORS preflight OK. Not verified: real browser, PostgreSQL e2e, containers, n8n, LLM, real data/models (see README "Pending").

## Next step
Decide branch/commit target; commit work units; user review of README "Pending" items.
