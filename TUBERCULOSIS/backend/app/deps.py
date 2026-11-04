from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit
from .db import get_db
from .models import AuditLog, User, UserSession
from .security import decode_token

PERMISSIONS: dict[str, set[str]] = {
    "operator": {"case:create", "case:read", "case:upload", "inference:run", "dashboard:read"},
    "reviewer": {"case:read", "review:create", "dashboard:read", "report:export"},
    "auditor": {"case:read", "audit:read", "dashboard:read", "report:export"},
}
# Machine account for n8n workflows (see app/service_token.py): no review, no user management.
PERMISSIONS["service"] = {"case:create", "case:read", "case:upload", "inference:run",
                          "dashboard:read", "report:export", "audit:read", "ops:write"}
PERMISSIONS["admin"] = {"users:manage", "audit:read", "case:create", "case:read", "case:upload",
                        "inference:run", "review:create", "dashboard:read", "report:export", "ops:write"}

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user: User
    sid: str


def _unauthorized(msg: str = "Not authenticated") -> HTTPException:
    return HTTPException(401, msg, headers={"WWW-Authenticate": "Bearer"})


def get_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> Principal:
    if creds is None:
        raise _unauthorized()
    try:
        claims = decode_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        _log_expired(db, creds.credentials)
        raise _unauthorized("Session expired")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid token")
    sess = db.get(UserSession, claims.get("sid"))
    user = db.get(User, int(claims["sub"])) if sess else None
    if sess is None or sess.revoked_at is not None or user is None or not user.is_active:
        raise _unauthorized("Session is not valid")
    return Principal(user=user, sid=sess.sid)


def _log_expired(db: Session, token: str) -> None:
    """Record session_expired once per session (identity read from the signed, expired token)."""
    try:
        claims = decode_token(token, verify_exp=False)
    except jwt.PyJWTError:
        return
    sid, uid = claims.get("sid"), int(claims.get("sub", 0))
    already = db.scalar(
        select(AuditLog.id).where(AuditLog.session_id == sid, AuditLog.event == "session_expired")
    )
    user = db.get(User, uid)
    if not already and user is not None:
        audit.record(db, event="session_expired", module="auth", user=user, session_id=sid)


def require(permission: str):
    def dep(p: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> Principal:
        if permission not in PERMISSIONS.get(p.user.role, set()):
            audit.record(db, event="permission_denied", module="auth", user=p.user, session_id=p.sid,
                         outcome="denied", detail={"required": permission})
            raise HTTPException(403, "Insufficient permissions")
        return p

    return dep
