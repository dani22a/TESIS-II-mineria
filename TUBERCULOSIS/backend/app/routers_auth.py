import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import audit
from .db import get_db
from .deps import PERMISSIONS, Principal, get_principal, require
from .models import User, UserSession, now
from .schemas import LoginIn, LogoutIn, RoleChange, TokenOut, UserCreate, UserOut, UserUpdate
from .security import create_token, hash_password, verify_password

router = APIRouter()


@router.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(body.password, user.hashed_password):
        audit.record(db, event="login", module="auth", user_id=user.id if user else None,
                     user_email=email, outcome="failure")
        raise HTTPException(401, "Invalid credentials")
    sid = str(uuid.uuid4())
    db.add(UserSession(sid=sid, user_id=user.id))
    db.commit()
    audit.record(db, event="login", module="auth", user=user, session_id=sid)
    return TokenOut(access_token=create_token(user.id, sid), role=user.role)


@router.post("/auth/logout", status_code=204, tags=["auth"])
def logout(body: LogoutIn | None = None, p: Principal = Depends(get_principal),
           db: Session = Depends(get_db)):
    if body and body.active_module:
        if body.active_module not in audit.MODULES:
            raise HTTPException(422, "Unknown module")
        audit.record(db, event="module_exit", module=body.active_module, user=p.user,
                     session_id=p.sid, client_event_id=body.client_event_id)
    sess = db.get(UserSession, p.sid)
    sess.revoked_at = now()
    db.commit()
    audit.record(db, event="logout", module="auth", user=p.user, session_id=p.sid)


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(p: Principal = Depends(get_principal)):
    return p.user


@router.get("/auth/permissions", tags=["auth"])
def my_permissions(p: Principal = Depends(get_principal)):
    return {"role": p.user.role, "permissions": sorted(PERMISSIONS[p.user.role])}


@router.get("/users", response_model=list[UserOut], tags=["users"])
def list_users(_: Principal = Depends(require("users:manage")), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201, tags=["users"])
def create_user(body: UserCreate, p: Principal = Depends(require("users:manage")),
                db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=email, full_name=body.full_name, role=body.role,
                hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    audit.record(db, event="user_created", module="users", user=p.user, session_id=p.sid,
                 detail={"target_user_id": user.id, "role": user.role})
    return user


@router.patch("/users/{user_id}", response_model=UserOut, tags=["users"])
def update_user(user_id: int, body: UserUpdate, p: Principal = Depends(require("users:manage")),
                db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    changes = body.model_dump(exclude_unset=True)
    if changes.get("is_active") is False:
        _guard_last_admin(db, user)
    for k, v in changes.items():
        setattr(user, k, v)
    db.commit()
    audit.record(db, event="user_updated", module="users", user=p.user, session_id=p.sid,
                 detail={"target_user_id": user.id, **changes})
    return user


@router.put("/users/{user_id}/role", response_model=UserOut, tags=["users"])
def change_role(user_id: int, body: RoleChange, p: Principal = Depends(require("users:manage")),
                db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    old = user.role
    if old == body.role:
        return user
    if old == "admin":
        _guard_last_admin(db, user)
    user.role = body.role
    db.commit()
    audit.record(db, event="permission_change", module="users", user=p.user, session_id=p.sid,
                 detail={"target_user_id": user.id, "from": old, "to": body.role})
    return user


def _guard_last_admin(db: Session, user: User) -> None:
    if user.role != "admin":
        return
    admins = db.scalar(select(func.count(User.id)).where(User.role == "admin", User.is_active))
    if admins <= 1:
        raise HTTPException(409, "Cannot remove the last active admin")
