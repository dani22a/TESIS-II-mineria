# SP-02 - Assisted pulmonary TB screening from chest X-rays

> **DEMO MODE.** Decision-support research prototype, NOT a diagnostic device. The inference engine
> shipped by default is a flagged DEMO (`is_demo=true`, `model_version=demo-0`): it is not a trained
> clinical model. The flag is shown in the API, the UI and every exported report. No performance
> claim is made anywhere in this repository.

## Repository layout

| Folder | Content |
|---|---|
| `backend/` | FastAPI + SQLAlchemy 2 + Alembic API (auth, roles, cases, upload + QC, inference, review, audit, dashboard, PDF/DOCX/XLSX reports, `/ops`) |
| `frontend/` | React + TypeScript (Vite) web app |
| `ml/` | Experimental pipeline: data prep, 5 models, Optuna, evaluation, Grad-CAM (see `ml/README.md`) |
| `workflows/` | n8n workflows WF-01..06 (see `workflows/README.md`) |
| `langchain-service/` | Aggregate-query + RAG service (see `langchain-service/README.md`) |
| `scripts/` | `e2e_smoke.py` golden-path test against a live server |
| `docs/` | `requisitos.md` (requirements, decisions, missing resources; Spanish) |

## Prerequisites

- Python 3.12, Node 20+ (tested with 24), a local PostgreSQL (tested with 18) with `createdb` / `psql`.
- Optional: `podman-compose` or `docker compose` (compose files are written but were NOT run: no container runtime was available).
- Optional: n8n (for workflows), an LLM API key (for langchain-service), GPU (for real training).

## Configuration

Copy `.env.example` to `backend/.env` (or export the variables). Frontend: `VITE_API_URL` (default `http://localhost:8000`).

```
DATABASE_URL=postgresql+psycopg://USER:PASS@localhost:5432/tb_screening
JWT_SECRET=<long random string>
STORAGE_DIR=./storage
CORS_ORIGINS=http://localhost:5173        # must match the frontend origin exactly
SEED_PASSWORD=<password for demo users>   # default Demo-Passw0rd! (demo only)
VITE_API_URL=http://localhost:8000
```

## Backend

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate      # or: source .venv/bin/activate
pip install -r requirements.txt
createdb tb_screening                                # local PostgreSQL
alembic upgrade head                                 # migrate
python -m app.seed                                   # demo users + demo cases (idempotent)
uvicorn app.main:app --reload                        # http://localhost:8000/docs
```

Demo users (password = `SEED_PASSWORD`): `admin@`, `operator@`, `reviewer@`, `auditor@` + `demo.local`.
Roles are enforced in the API: operator creates cases/uploads/runs inference; reviewer evaluates;
admin manages users, dashboard and exports; auditor reads the append-only audit log.

## Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # type-check + production build (dist/)
npm run preview -- --port 5173 --strictPort   # serve the build; backend CORS allows only CORS_ORIGINS
```

## Tests

```bash
cd backend && pytest -q                     # 38 tests (SQLite; set TEST_DATABASE_URL to use a disposable PostgreSQL)
cd ml && python -m pytest -q                # 13 tests
cd langchain-service && pytest -q           # 3 tests
```

## End-to-end smoke test (live server)

```bash
cd backend
python ../scripts/e2e_smoke.py --spawn                      # temp SQLite DB, migrate, seed, run uvicorn on a free port, test, stop
python ../scripts/e2e_smoke.py --base-url http://localhost:8000   # against a running, seeded server
```

Covers: login, case creation, valid + invalid upload, demo inference, reviewer evaluation, role denials,
dashboard, PDF/DOCX/XLSX export (re-opened and checked), and audit entries for login, module enter/exit and export.

## Containers (optional, untested)

```bash
podman-compose config
podman-compose up -d --build     # backend + frontend; PostgreSQL stays external (DATABASE_URL)
```

## n8n workflows

Import `workflows/*.json` (UI: Import from file, or `n8n import:workflow --separate --input=workflows/`), create the
credentials `TB SMTP` and `TB webhook header auth`, set the env vars in `workflows/README.md`, and generate the service token:

```bash
cd backend && python -m app.service_token --days 90      # store only as N8N_API_TOKEN
```

Workflows are exported inactive and have only been validated structurally.

## langchain-service

```bash
cd langchain-service && pip install -r requirements.txt
TB_API_URL=http://localhost:8000 TB_API_TOKEN=<service token> uvicorn app.main:app --port 8100
```

Works with no LLM (templated answers over aggregates). With `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` set and
`pip install -r requirements-llm.txt` an LLM phrases the answer; it only ever sees aggregate fields, never images or patient ids.
RAG docs in `langchain-service/docs/` are placeholders.

## ML pipeline

```bash
cd ml
pip install -r requirements.txt            # CPU torch: pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m tbml.smoke                       # SYNTHETIC end-to-end smoke test; outputs are plumbing checks, not results
```

Real training/evaluation (after placing data, see `ml/data/README.md`):

```bash
# 1. Put Shenzhen + Montgomery PNGs under /data/raw (any depth) and prepare a manifest
python -m tbml.data_prep --layout shenzhen --raw /data/raw --out data/processed/tb --size 224
# 2. Train 5 models with Optuna (TPE + pruner); Montgomery held out as external set
python -m tbml.train --manifest data/processed/tb/manifest.csv --out runs/exp1 \
    --trials 30 --epochs 15 --img-size 224 --external-institutions montgomery --mlflow
# 3. Metrics with patient-grouped bootstrap CIs, McNemar, DeLong, Holm
python -m tbml.evaluate --run runs/exp1 --n-boot 2000
# 4. Grad-CAM / attention rollout
python -m tbml.explain --run runs/exp1 --manifest data/processed/tb/manifest.csv --n 10
```

Friedman/Wilcoxon require a grouped-CV `cv_metrics.csv` (not automated yet). Never commit raw/processed images.

## Verification status (what was actually run)

Backend 38 tests, ml 13, langchain-service 3 passed; `npm run build` OK; `e2e_smoke.py --spawn` 26/26 checks;
built frontend served by `vite preview` on :5173 with the bundle pointing at `http://localhost:8000`, CORS preflight and
login from that origin return `access-control-allow-origin: http://localhost:5173`, and a foreign origin is refused.
Not verified: a real browser session (no UI click-through), PostgreSQL run of the e2e script, containers, n8n, an LLM.

## Pending (data, credentials, compute)

- Real datasets: Shenzhen/Montgomery download and licence check; MIMIC-CXR / VinDr-CXR need PhysioNet credentialed access (CITI + DUA).
- A trained model: the default engine is the demo; real weights, calibration and threshold require the ML pipeline on real data.
- Compute: no GPU locally (Colab/server needed for 5 models x Optuna); pretrained-weight source and licences to be decided.
- Lung segmentation is a placeholder; Friedman/Wilcoxon CV loop not automated.
- Credentials: SMTP and webhook header auth for n8n, LLM API key (optional), authorised clinical documents for RAG.
- Infra: container runtime to run compose; a live n8n instance to test WF-01..06; production secrets (`JWT_SECRET`) and HTTPS.
- Ethics/regulatory: institutional approval and clinical validation before any use beyond research.

See `docs/requisitos.md` for requirements and decisions.
