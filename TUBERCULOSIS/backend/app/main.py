from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .routers_audit import router as audit_router
from .routers_auth import router as auth_router
from .routers_cases import router as cases_router
from .routers_ops import router as ops_router
from .routers_reports import router as reports_router

app = FastAPI(title="SP-02 TB screening API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(audit_router)
app.include_router(reports_router)
app.include_router(ops_router)


@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "engine": "demo", "demo_mode": True}
