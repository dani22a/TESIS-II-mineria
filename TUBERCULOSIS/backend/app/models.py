import secrets
from datetime import UTC, datetime

from sqlalchemy import (BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

ROLES = ("admin", "operator", "reviewer", "auditor", "service")


def now() -> datetime:
    return datetime.now(UTC)


def new_pseudonym() -> str:
    return "TB-" + secrets.token_hex(5).upper()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserSession(Base):
    __tablename__ = "user_sessions"
    sid: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pseudonym_id: Mapped[str] = mapped_column(String(32), unique=True, default=new_pseudonym)
    institution: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # created | image_uploaded | processing | completed | not_evaluable | technical_failure
    status: Mapped[str] = mapped_column(String(20), default="created")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    image_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_format: Mapped[str | None] = mapped_column(String(10), nullable=True)
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qc_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    qc_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class InferenceResult(Base):
    __tablename__ = "inference_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))  # completed | not_evaluable | technical_failure
    label: Mapped[str | None] = mapped_column(String(30), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(50))
    is_demo: Mapped[bool] = mapped_column(Boolean)
    error_message: Mapped[str | None] = mapped_column(String(300), nullable=True)
    heatmap_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReviewerEvaluation(Base):
    __tablename__ = "reviewer_evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    inference_id: Mapped[int] = mapped_column(ForeignKey("inference_results.id"))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    agrees: Mapped[bool] = mapped_column(Boolean)
    final_label: Mapped[str] = mapped_column(String(30))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    """Append-only: UPDATE/DELETE/TRUNCATE are blocked by DB triggers (see audit_guards)."""

    __tablename__ = "audit_log"
    __table_args__ = (UniqueConstraint("user_id", "client_event_id", name="uq_audit_client_event"),)
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(50), index=True)
    event: Mapped[str] = mapped_column(String(50), index=True)
    outcome: Mapped[str] = mapped_column(String(20))  # success | failure | denied
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
