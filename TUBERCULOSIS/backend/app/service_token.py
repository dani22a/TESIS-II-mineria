"""Create (or reuse) the n8n service account and print a long-lived bearer token.

    python -m app.service_token [--days 90]

Revoke by deactivating the user (PATCH /users/{id}) or logging the session out. The token is
printed once to stdout; store it as the N8N_API_TOKEN environment variable, never in a workflow.
"""
import argparse
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit
from .db import SessionLocal
from .models import User, UserSession
from .security import create_token, hash_password

EMAIL = "n8n-service@system.local"


def issue(db: Session, days: int = 90) -> str:
    user = db.scalar(select(User).where(User.email == EMAIL))
    if user is None:
        user = User(email=EMAIL, full_name="n8n service account", role="service",
                    hashed_password=hash_password(secrets.token_urlsafe(32)))  # password unusable
        db.add(user)
        db.commit()
    sid = str(uuid.uuid4())
    db.add(UserSession(sid=sid, user_id=user.id))
    db.commit()
    audit.record(db, event="service_token_issued", module="auth", user=user, session_id=sid,
                 detail={"days": days})
    return create_token(user.id, sid, ttl=timedelta(days=days))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    with SessionLocal() as s:
        print(issue(s, ap.parse_args().days))
