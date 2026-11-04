from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from . import audit
from .db import get_db
from .deps import Principal, require
from .report_data import Filters, build_summary
from .report_render import RENDERERS

router = APIRouter(tags=["dashboard"])


def filters(date_from: datetime | None = None, date_to: datetime | None = None,
            status: str | None = None, model_version: str | None = None) -> Filters:
    return Filters(date_from, date_to, status, model_version)


@router.get("/dashboard/summary")
def summary(_: Principal = Depends(require("dashboard:read")), db: Session = Depends(get_db),
            f: Filters = Depends(filters)):
    return build_summary(db, f)


@router.get("/reports/{kind}.{fmt}", tags=["reports"])
def export_report(kind: Literal["operational", "management"], fmt: Literal["pdf", "docx", "xlsx"],
                  p: Principal = Depends(require("report:export")), db: Session = Depends(get_db),
                  f: Filters = Depends(filters)):
    data = build_summary(db, f)
    render, media = RENDERERS[fmt]
    body = render(data, kind)
    audit.record_export(db, p.user, p.sid, "reports",
                        {"report": kind, "format": fmt, "filters": data["filters"],
                         "is_demo": data["is_demo"], "total_cases": data["operational"]["total_cases"]})
    return Response(body, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="tb-{kind}-report.{fmt}"',
        "Cache-Control": "private, no-store"})
