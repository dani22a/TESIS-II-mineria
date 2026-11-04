"""Single source of truth for dashboard and reports (same filters, same numbers)."""
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Case, InferenceResult, ReviewerEvaluation

STATUSES = ("created", "image_uploaded", "processing", "completed", "not_evaluable", "technical_failure")


@dataclass
class Filters:
    date_from: datetime | None = None
    date_to: datetime | None = None
    status: str | None = None
    model_version: str | None = None

    def as_dict(self) -> dict:
        return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in vars(self).items() if v}


def _aware(d: datetime | None) -> datetime | None:
    return d if d is None or d.tzinfo else d.replace(tzinfo=UTC)


def _latest_inferences(db: Session) -> dict[int, InferenceResult]:
    latest: dict[int, InferenceResult] = {}
    for r in db.scalars(select(InferenceResult).order_by(InferenceResult.id)):
        latest[r.case_id] = r
    return latest


def build_summary(db: Session, f: Filters) -> dict:
    latest = _latest_inferences(db)
    cases = []
    for c in db.scalars(select(Case).order_by(Case.id)):
        created = _aware(c.created_at)
        if f.date_from and created < _aware(f.date_from):
            continue
        if f.date_to and created > _aware(f.date_to):
            continue
        if f.status and c.status != f.status:
            continue
        inf = latest.get(c.id)
        if f.model_version and (inf is None or inf.model_version != f.model_version):
            continue
        cases.append((c, inf))
    ids = {c.id for c, _ in cases}
    infs = [i for _, i in cases if i is not None]
    by_status = Counter(c.status for c, _ in cases)
    by_result = Counter((i.label or i.status) for i in infs)
    by_model = Counter(i.model_version for i in infs)
    secs = [(_aware(i.created_at) - _aware(c.created_at)).total_seconds() for c, i in cases
            if i is not None and i.status == "completed"]
    reviews = [r for r in db.scalars(select(ReviewerEvaluation)) if r.case_id in ids]
    is_demo = any(i.is_demo for i in infs)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "filters": f.as_dict(),
        "is_demo": is_demo,
        "demo_notice": "DEMO MODE: results come from a demonstration engine, not a validated model."
        if is_demo else None,
        "operational": {
            "total_cases": len(cases),
            "cases_by_status": {s: by_status.get(s, 0) for s in STATUSES},
            "results_by_outcome": dict(by_result),
            "inferences_by_model_version": dict(by_model),
            "processing_seconds": {
                "n": len(secs),
                "mean": round(mean(secs), 3) if secs else None,
                "median": round(median(secs), 3) if secs else None,
                "max": round(max(secs), 3) if secs else None,
            },
            "technical_failures": by_status.get("technical_failure", 0),
            "not_evaluable": by_status.get("not_evaluable", 0),
            "reviews": {"total": len(reviews), "agreed": sum(r.agrees for r in reviews),
                        "disagreed": sum(not r.agrees for r in reviews)},
        },
        "scientific": {
            "available": False,
            "is_demo": is_demo,
            "reason": "No reference-standard labels are loaded and no validated model is deployed; "
                      "sensitivity/specificity/AUC are not computed. Reviewer agreement is an "
                      "operational indicator, not ground truth.",
        },
    }
