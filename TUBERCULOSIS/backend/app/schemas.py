from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["admin", "operator", "reviewer", "auditor", "service"]
FinalLabel = Literal["probable_tuberculosis", "no_compatible_findings", "not_evaluable"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class LogoutIn(BaseModel):
    active_module: str | None = None
    client_event_id: str | None = Field(default=None, max_length=64)


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=72)
    role: Role


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


class RoleChange(BaseModel):
    role: Role


class CaseCreate(BaseModel):
    institution: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class InferenceOut(ORM):
    id: int
    case_id: int
    status: str
    label: str | None
    score: float | None
    threshold: float
    model_version: str
    is_demo: bool
    error_message: str | None
    has_heatmap: bool = False
    created_at: datetime


class CaseOut(ORM):
    id: int
    pseudonym_id: str
    institution: str | None
    notes: str | None
    status: str
    created_at: datetime
    has_image: bool = False
    qc_passed: bool | None
    qc_reason: str | None
    image_width: int | None
    image_height: int | None
    latest_inference: InferenceOut | None = None


class ReviewIn(BaseModel):
    inference_id: int | None = None  # defaults to the latest inference
    agrees: bool
    final_label: FinalLabel
    comment: str | None = Field(default=None, max_length=2000)


class ReviewOut(ORM):
    id: int
    case_id: int
    inference_id: int
    reviewer_id: int
    agrees: bool
    final_label: str
    comment: str | None
    created_at: datetime


class ModuleEventIn(BaseModel):
    event: Literal["module_enter", "module_exit"]
    module: str
    client_event_id: str = Field(min_length=8, max_length=64)


class AuditOut(ORM):
    id: int
    created_at: datetime
    user_id: int | None
    user_email: str | None
    session_id: str | None
    module: str
    event: str
    outcome: str
    detail: str | None
