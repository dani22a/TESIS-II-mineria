import hashlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit
from .config import settings
from .db import get_db
from .deps import Principal, require
from .imaging import InvalidUpload, quality_control, validate_upload
from .inference import LABEL_NEG, LABEL_TB, InferenceEngine, get_engine
from .models import Case, InferenceResult, ReviewerEvaluation
from .schemas import CaseCreate, CaseOut, InferenceOut, ReviewIn, ReviewOut
from .storage import Storage, get_storage

router = APIRouter(tags=["cases"])


def _latest(db: Session, case_id: int) -> InferenceResult | None:
    return db.scalar(select(InferenceResult).where(InferenceResult.case_id == case_id)
                     .order_by(InferenceResult.id.desc()).limit(1))


def _inf_out(r: InferenceResult | None) -> InferenceOut | None:
    if r is None:
        return None
    out = InferenceOut.model_validate(r)
    out.has_heatmap = r.heatmap_key is not None
    return out


def _case_out(db: Session, c: Case) -> CaseOut:
    out = CaseOut.model_validate(c)
    out.has_image = c.image_key is not None
    out.latest_inference = _inf_out(_latest(db, c.id))
    return out


def _get_case(db: Session, case_id: int) -> Case:
    c = db.get(Case, case_id)
    if c is None:
        raise HTTPException(404, "Case not found")
    return c


@router.post("/cases", response_model=CaseOut, status_code=201)
def create_case(body: CaseCreate, p: Principal = Depends(require("case:create")),
                db: Session = Depends(get_db)):
    c = Case(institution=body.institution, notes=body.notes, created_by=p.user.id)
    db.add(c)
    db.commit()
    audit.record(db, event="case_created", module="cases", user=p.user, session_id=p.sid,
                 detail={"case_id": c.id, "pseudonym_id": c.pseudonym_id})
    return _case_out(db, c)


@router.get("/cases", response_model=list[CaseOut])
def list_cases(_: Principal = Depends(require("case:read")), db: Session = Depends(get_db),
               status: str | None = None, limit: int = 100, offset: int = 0):
    q = select(Case).order_by(Case.id.desc()).limit(min(limit, 500)).offset(max(offset, 0))
    if status:
        q = q.where(Case.status == status)
    return [_case_out(db, c) for c in db.scalars(q)]


@router.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int, _: Principal = Depends(require("case:read")),
             db: Session = Depends(get_db)):
    return _case_out(db, _get_case(db, case_id))


@router.post("/cases/{case_id}/image", response_model=CaseOut, status_code=201)
async def upload_image(case_id: int, file: UploadFile = File(...),
                       p: Principal = Depends(require("case:upload")),
                       db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    case = _get_case(db, case_id)
    if case.image_key:
        raise HTTPException(409, "Case already has an image")
    data = await file.read(settings.max_upload_bytes + 1)
    try:
        fmt = validate_upload(data, file.content_type)
    except InvalidUpload as e:
        audit.record(db, event="image_upload", module="upload", user=p.user, session_id=p.sid,
                     outcome="failure", detail={"case_id": case.id, "reason": e.message})
        raise HTTPException(e.status, e.message)
    qc = quality_control(data)
    key = f"images/{uuid.uuid4().hex}.{'jpg' if fmt == 'jpeg' else fmt}"  # original filename is discarded
    storage.put(key, data)
    case.image_key, case.image_format = key, fmt
    case.image_sha256 = hashlib.sha256(data).hexdigest()
    case.image_width, case.image_height = qc.width, qc.height
    case.qc_passed, case.qc_reason = qc.passed, qc.reason
    case.status = "image_uploaded" if qc.passed else "not_evaluable"
    db.commit()
    audit.record(db, event="image_upload", module="upload", user=p.user, session_id=p.sid,
                 detail={"case_id": case.id, "qc_passed": qc.passed, "qc_reason": qc.reason})
    return _case_out(db, case)


@router.get("/cases/{case_id}/image")
def download_image(case_id: int, _: Principal = Depends(require("case:read")),
                   db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    case = _get_case(db, case_id)
    if not case.image_key:
        raise HTTPException(404, "No image")
    return Response(storage.get(case.image_key), media_type=f"image/{case.image_format}",
                    headers={"Cache-Control": "private, no-store"})


@router.post("/cases/{case_id}/inference", response_model=InferenceOut, status_code=201)
def run_inference(case_id: int, p: Principal = Depends(require("inference:run")),
                  db: Session = Depends(get_db), storage: Storage = Depends(get_storage),
                  engine: InferenceEngine = Depends(get_engine)):
    case = _get_case(db, case_id)
    if not case.image_key:
        raise HTTPException(409, "Case has no image")
    base = dict(case_id=case.id, threshold=settings.decision_threshold,
                model_version=engine.model_version, is_demo=engine.is_demo, created_by=p.user.id)
    if case.qc_passed is False:  # not evaluable: the engine is never called
        res = InferenceResult(status="not_evaluable", error_message=case.qc_reason, **base)
        case.status = "not_evaluable"
    else:
        case.status = "processing"
        db.commit()
        try:
            pred = engine.predict(storage.get(case.image_key))
            hkey = None
            if pred.heatmap_png:
                hkey = f"heatmaps/{uuid.uuid4().hex}.png"
                storage.put(hkey, pred.heatmap_png)
            label = LABEL_TB if pred.score >= settings.decision_threshold else LABEL_NEG
            res = InferenceResult(status="completed", label=label, score=pred.score,
                                  heatmap_key=hkey, **base)
            case.status = "completed"
        except Exception as e:  # technical failure, distinct from not_evaluable
            res = InferenceResult(status="technical_failure",
                                  error_message=f"{type(e).__name__}: {e}"[:300], **base)
            case.status = "technical_failure"
    db.add(res)
    db.commit()
    audit.record(db, event="inference_run", module="results", user=p.user, session_id=p.sid,
                 outcome="failure" if res.status == "technical_failure" else "success",
                 detail={"case_id": case.id, "inference_id": res.id, "status": res.status,
                         "model_version": res.model_version, "is_demo": res.is_demo})
    return _inf_out(res)


@router.get("/cases/{case_id}/inferences", response_model=list[InferenceOut])
def list_inferences(case_id: int, _: Principal = Depends(require("case:read")),
                    db: Session = Depends(get_db)):
    _get_case(db, case_id)
    rows = db.scalars(select(InferenceResult).where(InferenceResult.case_id == case_id)
                      .order_by(InferenceResult.id.desc()))
    return [_inf_out(r) for r in rows]


@router.get("/cases/{case_id}/inferences/{inference_id}/heatmap")
def heatmap(case_id: int, inference_id: int, _: Principal = Depends(require("case:read")),
            db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    r = db.get(InferenceResult, inference_id)
    if r is None or r.case_id != case_id or not r.heatmap_key:
        raise HTTPException(404, "No heatmap")
    return Response(storage.get(r.heatmap_key), media_type="image/png",
                    headers={"Cache-Control": "private, no-store"})


@router.post("/cases/{case_id}/reviews", response_model=ReviewOut, status_code=201)
def create_review(case_id: int, body: ReviewIn, p: Principal = Depends(require("review:create")),
                  db: Session = Depends(get_db)):
    _get_case(db, case_id)
    inf = db.get(InferenceResult, body.inference_id) if body.inference_id else _latest(db, case_id)
    if inf is None or inf.case_id != case_id:
        raise HTTPException(409, "No inference to review")
    if inf.status == "technical_failure":
        raise HTTPException(409, "Cannot review a technical failure; re-run inference")
    rev = ReviewerEvaluation(case_id=case_id, inference_id=inf.id, reviewer_id=p.user.id,
                             agrees=body.agrees, final_label=body.final_label, comment=body.comment)
    db.add(rev)
    db.commit()
    audit.record(db, event="review_created", module="review", user=p.user, session_id=p.sid,
                 detail={"case_id": case_id, "inference_id": inf.id, "agrees": body.agrees,
                         "final_label": body.final_label})
    return rev


@router.get("/cases/{case_id}/reviews", response_model=list[ReviewOut])
def list_reviews(case_id: int, _: Principal = Depends(require("case:read")),
                 db: Session = Depends(get_db)):
    _get_case(db, case_id)
    return db.scalars(select(ReviewerEvaluation).where(ReviewerEvaluation.case_id == case_id)
                      .order_by(ReviewerEvaluation.id)).all()
