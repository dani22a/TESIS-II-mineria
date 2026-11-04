from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit
from .db import get_db
from .deps import Principal, get_principal, require
from .models import AuditLog
from .schemas import AuditOut, ModuleEventIn

router = APIRouter(tags=["audit"])


@router.post("/audit/module-events", status_code=201)
def module_event(body: ModuleEventIn, p: Principal = Depends(get_principal),
                 db: Session = Depends(get_db)):
    """Module enter/exit observed by the client. Identity and session come from the JWT only;
    a repeated client_event_id (retry) is a no-op."""
    if body.module not in audit.MODULES:
        raise HTTPException(422, "Unknown module")
    row, created = audit.record(db, event=body.event, module=body.module, user=p.user,
                                session_id=p.sid, client_event_id=body.client_event_id)
    return {"id": row.id, "duplicate": not created}


@router.get("/audit", response_model=list[AuditOut])
def query_audit(
    _: Principal = Depends(require("audit:read")),
    db: Session = Depends(get_db),
    user_id: int | None = None,
    module: str | None = None,
    event: str | None = None,
    outcome: str | None = None,
    session_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    q = select(AuditLog)
    for col, val in ((AuditLog.user_id, user_id), (AuditLog.module, module), (AuditLog.event, event),
                     (AuditLog.outcome, outcome), (AuditLog.session_id, session_id)):
        if val is not None:
            q = q.where(col == val)
    if date_from:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to:
        q = q.where(AuditLog.created_at <= date_to)
    return db.scalars(q.order_by(AuditLog.id.desc()).limit(limit).offset(offset)).all()
