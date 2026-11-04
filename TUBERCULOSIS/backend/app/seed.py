"""Seed demo users (one per role) and demo cases. Idempotent. Run: python -m app.seed"""
import io

import numpy as np
from PIL import Image
from sqlalchemy import select

from .config import settings
from .db import SessionLocal
from .inference import DemoEngine
from .models import Case, InferenceResult, User
from .security import hash_password
from .storage import LocalStorage

USERS = [
    ("admin@demo.local", "Demo Admin", "admin"),
    ("operator@demo.local", "Demo Operator", "operator"),
    ("reviewer@demo.local", "Demo Reviewer", "reviewer"),
    ("auditor@demo.local", "Demo Auditor", "auditor"),
]


def _png(seed: int | None, size: int = 512) -> bytes:
    if seed is None:  # uniform image -> fails QC
        arr = np.full((size, size), 128, dtype=np.uint8)
    else:
        rng = np.random.default_rng(seed)
        y, x = np.mgrid[0:size, 0:size]
        arr = (90 + 80 * np.exp(-((x - size / 2) ** 2 + (y - size / 2) ** 2) / (2 * 150.0**2))
               + rng.normal(0, 20, (size, size))).clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def main() -> None:
    storage = LocalStorage(settings.storage_dir)
    engine = DemoEngine()
    with SessionLocal() as db:
        for email, name, role in USERS:
            if not db.scalar(select(User).where(User.email == email)):
                db.add(User(email=email, full_name=name, role=role,
                            hashed_password=hash_password(settings.seed_password)))
        db.commit()
        if db.scalar(select(Case.id).limit(1)):
            print("Cases already present; skipping demo cases.")
            return
        op = db.scalar(select(User).where(User.email == "operator@demo.local"))
        for seed, note in ((1, "Demo case A"), (2, "Demo case B"), (None, "Demo case with blank image"), ("none", "Demo case without image")):
            case = Case(notes=note, institution="Demo Hospital", created_by=op.id)
            db.add(case)
            db.flush()
            if seed == "none":
                db.commit()
                continue
            data = _png(seed)
            key = f"images/seed-{case.id}.png"
            storage.put(key, data)
            case.image_key, case.image_format = key, "png"
            case.image_width = case.image_height = 512
            if seed is None:
                case.qc_passed, case.qc_reason, case.status = False, "blank or uniform image", "not_evaluable"
                db.add(InferenceResult(case_id=case.id, status="not_evaluable", threshold=settings.decision_threshold,
                                       model_version=engine.model_version, is_demo=True,
                                       error_message=case.qc_reason, created_by=op.id))
            else:
                case.qc_passed, case.status = True, "completed"
                pred = engine.predict(data)
                hkey = f"heatmaps/seed-{case.id}.png"
                storage.put(hkey, pred.heatmap_png)
                db.add(InferenceResult(
                    case_id=case.id, status="completed", score=pred.score, heatmap_key=hkey,
                    label="probable_tuberculosis" if pred.score >= settings.decision_threshold else "no_compatible_findings",
                    threshold=settings.decision_threshold, model_version=engine.model_version,
                    is_demo=True, created_by=op.id))
            db.commit()
    print(f"Seeded users ({settings.seed_password!r} password) and demo cases.")


if __name__ == "__main__":
    main()
