"""Operational endpoints for automation (n8n). Business rules and audit stay in the API."""
from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit
from .db import get_db
from .deps import Principal, require
from .models import Case, InferenceResult, ReviewerEvaluation

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/pending-review")
def pending_review(_: Principal = Depends(require("case:read")), db: Session = Depends(get_db)):
    """Cases whose latest inference is completed and that have no reviewer evaluation yet."""
    reviewed = set(db.scalars(select(ReviewerEvaluation.case_id)))
    latest: dict[int, InferenceResult] = {}
    for r in db.scalars(select(InferenceResult).order_by(InferenceResult.id)):
        latest[r.case_id] = r
    items = [{"case_id": cid, "inference_id": r.id, "label": r.label, "is_demo": r.is_demo,
              "created_at": r.created_at.isoformat()}
             for cid, r in latest.items() if r.status == "completed" and cid not in reviewed]
    return {"count": len(items), "items": items}


@router.get("/qc")
def qc_report(_: Principal = Depends(require("case:read")), db: Session = Depends(get_db)):
    """Data-quality findings: duplicate images (same SHA-256), cases without image, failed QC."""
    by_hash: dict[str, list[int]] = defaultdict(list)
    missing, invalid = [], []
    for c in db.scalars(select(Case).order_by(Case.id)):
        if c.image_key is None:
            missing.append(c.id)
            continue
        if c.image_sha256:
            by_hash[c.image_sha256].append(c.id)
        if c.qc_passed is False:
            invalid.append({"case_id": c.id, "reason": c.qc_reason})
    dups = [{"sha256_prefix": h[:12], "case_ids": ids} for h, ids in by_hash.items() if len(ids) > 1]
    return {"duplicates": dups, "missing_image": missing, "invalid": invalid,
            "total_findings": len(dups) + len(missing) + len(invalid)}


class OpsEvent(BaseModel):
    workflow: str = Field(min_length=1, max_length=40)
    event: str = Field(min_length=1, max_length=40)
    outcome: Literal["success", "failure"] = "success"
    detail: dict | None = None


@router.post("/events", status_code=201)
def log_event(body: OpsEvent, p: Principal = Depends(require("ops:write")),
              db: Session = Depends(get_db)):
    """Append an automation event to the audit log (identity comes from the JWT)."""
    row, _ = audit.record(db, event=f"wf_{body.event}"[:50], module="ops", user=p.user,
                          session_id=p.sid, outcome=body.outcome,
                          detail={"workflow": body.workflow, **(body.detail or {})})
    return {"id": row.id}
