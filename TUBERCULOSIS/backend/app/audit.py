"""Audit service. Every call commits its own row; the table is append-only (DB triggers)."""
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import AuditLog, User

MODULES = {"auth", "cases", "upload", "results", "review", "dashboard", "audit", "users", "reports", "ops"}


def record(
    db: Session,
    *,
    event: str,
    module: str,
    user: User | None = None,
    user_id: int | None = None,
    user_email: str | None = None,
    session_id: str | None = None,
    outcome: str = "success",
    detail: dict | None = None,
    client_event_id: str | None = None,
) -> tuple[AuditLog, bool]:
    """Insert an audit row. Returns (row, created). Idempotent on (user, client_event_id)."""
    if user is not None:
        user_id, user_email = user.id, user.email
    if client_event_id and user_id is not None:
        existing = _find(db, user_id, client_event_id)
        if existing:
            return existing, False
    row = AuditLog(
        user_id=user_id,
        user_email=user_email,
        session_id=session_id,
        module=module,
        event=event,
        outcome=outcome,
        detail=json.dumps(detail, default=str) if detail else None,
        client_event_id=client_event_id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:  # concurrent retry with the same client_event_id
        db.rollback()
        existing = _find(db, user_id, client_event_id) if client_event_id and user_id else None
        if existing:
            return existing, False
        raise
    return row, True


def _find(db: Session, user_id: int, client_event_id: str) -> AuditLog | None:
    return db.scalar(
        select(AuditLog).where(
            AuditLog.user_id == user_id, AuditLog.client_event_id == client_event_id
        )
    )


def record_export(db: Session, user: User, session_id: str | None, module: str, detail: dict) -> AuditLog:
    """Hook for reports/exports (T3): call right before returning an exported file."""
    return record(db, event="export", module=module, user=user, session_id=session_id, detail=detail)[0]
