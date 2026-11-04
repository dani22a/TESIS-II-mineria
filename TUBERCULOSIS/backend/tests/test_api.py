from datetime import timedelta

import pytest
from sqlalchemy import text

from app.config import settings
from app.security import create_token

from .conftest import make_png

PNG = ("x.png", None, "image/png")


def upload(client, headers, case_id, data, ctype="image/png", name="x.png"):
    return client.post(f"/cases/{case_id}/image", headers=headers, files={"file": (name, data, ctype)})


def new_case(client, headers):
    r = client.post("/cases", headers=headers, json={"institution": "H1"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def audit_events(client, headers, **params):
    r = client.get("/audit", headers=headers, params={"limit": 500, **params})
    assert r.status_code == 200, r.text
    return r.json()


# ---------- permissions ----------
def test_unauthenticated_is_401(client):
    assert client.get("/cases").status_code == 401
    assert client.get("/audit").status_code == 401


@pytest.mark.parametrize(
    "role,method,path,expected",
    [
        ("operator", "get", "/users", 403),
        ("reviewer", "post", "/cases", 403),
        ("auditor", "post", "/cases", 403),
        ("auditor", "get", "/users", 403),
        ("operator", "get", "/audit", 403),
        ("reviewer", "get", "/audit", 403),
        ("reviewer", "post", "/cases/1/inference", 403),
        ("operator", "post", "/cases/1/reviews", 403),
        ("auditor", "get", "/audit", 200),
        ("admin", "get", "/audit", 200),
        ("admin", "get", "/users", 200),
        ("auditor", "get", "/cases", 200),
    ],
)
def test_role_matrix(client, auth, role, method, path, expected):
    kwargs = {"json": {"agrees": True, "final_label": "not_evaluable"}} if method == "post" and "reviews" in path else {}
    r = getattr(client, method)(path, headers=auth[role], **kwargs)
    assert r.status_code == expected, r.text


def test_denied_access_is_audited(client, auth):
    client.get("/users", headers=auth["operator"])
    rows = audit_events(client, auth["auditor"], event="permission_denied")
    assert rows and rows[0]["outcome"] == "denied" and rows[0]["user_email"] == "operator@test.local"


def test_role_change_is_audited_and_enforced(client, auth):
    users = client.get("/users", headers=auth["admin"]).json()
    op = next(u for u in users if u["role"] == "operator")
    assert client.put(f"/users/{op['id']}/role", headers=auth["operator"], json={"role": "admin"}).status_code == 403
    r = client.put(f"/users/{op['id']}/role", headers=auth["admin"], json={"role": "reviewer"})
    assert r.status_code == 200 and r.json()["role"] == "reviewer"
    # the old operator token now carries reviewer permissions (role read from DB on every call)
    assert client.post("/cases", headers=auth["operator"], json={}).status_code == 403
    ev = audit_events(client, auth["auditor"], event="permission_change")
    assert len(ev) == 1 and '"from": "operator"' in ev[0]["detail"] and '"to": "reviewer"' in ev[0]["detail"]


def test_cannot_demote_last_admin(client, auth):
    admin = next(u for u in client.get("/users", headers=auth["admin"]).json() if u["role"] == "admin")
    r = client.put(f"/users/{admin['id']}/role", headers=auth["admin"], json={"role": "operator"})
    assert r.status_code == 409


# ---------- upload validation / QC ----------
def test_invalid_files_rejected(client, auth, tmp_path):
    cid = new_case(client, auth["operator"])
    assert upload(client, auth["operator"], cid, b"hello world, not an image").status_code == 415
    assert upload(client, auth["operator"], cid, make_png(), ctype="image/jpeg").status_code == 415  # mime mismatch
    assert upload(client, auth["operator"], cid, b"").status_code == 400
    assert upload(client, auth["operator"], cid, b"\x89PNG\r\n\x1a\n" + b"garbage" * 20).status_code == 422
    case = client.get(f"/cases/{cid}", headers=auth["operator"]).json()
    assert case["has_image"] is False and case["status"] == "created"
    fails = [e for e in audit_events(client, auth["auditor"], event="image_upload") if e["outcome"] == "failure"]
    assert len(fails) == 4


def test_oversized_file_rejected(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 1000)
    cid = new_case(client, auth["operator"])
    assert upload(client, auth["operator"], cid, make_png()).status_code == 413


def test_auditor_cannot_upload(client, auth):
    cid = new_case(client, auth["operator"])
    assert upload(client, auth["auditor"], cid, make_png()).status_code == 403


@pytest.mark.parametrize("kwargs,reason", [({"uniform": True}, "uniform"), ({"size": 128}, "resolution")])
def test_qc_failure_is_not_evaluable(client, auth, kwargs, reason):
    cid = new_case(client, auth["operator"])
    r = upload(client, auth["operator"], cid, make_png(**kwargs))
    assert r.status_code == 201
    body = r.json()
    assert body["qc_passed"] is False and reason in body["qc_reason"] and body["status"] == "not_evaluable"
    inf = client.post(f"/cases/{cid}/inference", headers=auth["operator"]).json()
    assert inf["status"] == "not_evaluable" and inf["label"] is None and inf["score"] is None


# ---------- inference ----------
def test_demo_inference_is_flagged_and_deterministic(client, auth):
    scores = []
    for _ in range(2):
        cid = new_case(client, auth["operator"])
        upload(client, auth["operator"], cid, make_png(seed=7))
        inf = client.post(f"/cases/{cid}/inference", headers=auth["operator"]).json()
        assert inf["is_demo"] is True and inf["model_version"] == "demo-0"
        assert inf["threshold"] == settings.decision_threshold and inf["status"] == "completed"
        assert inf["label"] in {"probable_tuberculosis", "no_compatible_findings"} and inf["has_heatmap"]
        scores.append(inf["score"])
    assert scores[0] == scores[1]


def test_inference_failure_is_technical_failure(client, auth, failing_engine):
    cid = new_case(client, auth["operator"])
    upload(client, auth["operator"], cid, make_png())
    r = client.post(f"/cases/{cid}/inference", headers=auth["operator"])
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "technical_failure" and "model crashed" in body["error_message"]
    assert body["label"] is None and body["model_version"] == "failing-0"
    assert client.get(f"/cases/{cid}", headers=auth["operator"]).json()["status"] == "technical_failure"
    # cannot be reviewed; failure is audited as such
    rv = client.post(f"/cases/{cid}/reviews", headers=auth["reviewer"],
                     json={"agrees": True, "final_label": "not_evaluable"})
    assert rv.status_code == 409
    ev = audit_events(client, auth["auditor"], event="inference_run")
    assert ev[0]["outcome"] == "failure"


def test_inference_requires_image(client, auth):
    cid = new_case(client, auth["operator"])
    assert client.post(f"/cases/{cid}/inference", headers=auth["operator"]).status_code == 409


# ---------- audit: module events, immutability, sessions ----------
def test_module_events_idempotent_and_identity_from_jwt(client, auth):
    body = {"event": "module_enter", "module": "cases", "client_event_id": "evt-0000001"}
    r1 = client.post("/audit/module-events", headers=auth["operator"], json={**body, "user_id": 999})
    r2 = client.post("/audit/module-events", headers=auth["operator"], json=body)
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["duplicate"] is False and r2.json()["duplicate"] is True
    assert r1.json()["id"] == r2.json()["id"]
    exit_ = {"event": "module_exit", "module": "cases", "client_event_id": "evt-0000002"}
    client.post("/audit/module-events", headers=auth["operator"], json=exit_)
    rows = audit_events(client, auth["auditor"], module="cases")
    enters = [r for r in rows if r["event"] == "module_enter"]
    assert len(enters) == 1 and enters[0]["user_email"] == "operator@test.local" and enters[0]["session_id"]
    assert len([r for r in rows if r["event"] == "module_exit"]) == 1
    bad = client.post("/audit/module-events", headers=auth["operator"], json={**body, "module": "nope", "client_event_id": "evt-0000003"})
    assert bad.status_code == 422


def test_logout_records_exit_and_revokes_session(client, auth):
    h = auth["operator"]
    r = client.post("/auth/logout", headers=h, json={"active_module": "cases", "client_event_id": "evt-logout-1"})
    assert r.status_code == 204
    assert client.get("/cases", headers=h).status_code == 401
    names = [e["event"] for e in audit_events(client, auth["auditor"], user_id=_uid(client, auth, "operator"))]
    assert "logout" in names and "module_exit" in names


def _uid(client, auth, role):
    return next(u["id"] for u in client.get("/users", headers=auth["admin"]).json() if u["role"] == role)


def test_expired_token_logs_session_expired_once(client, auth):
    with client.session_factory() as s:
        sid = s.execute(text("select sid from user_sessions limit 1")).scalar()
        uid = s.execute(text("select user_id from user_sessions where sid=:s"), {"s": sid}).scalar()
    old = {"Authorization": "Bearer " + create_token(uid, sid, ttl=timedelta(seconds=-5))}
    assert client.get("/cases", headers=old).status_code == 401
    assert client.get("/cases", headers=old).status_code == 401
    assert len(audit_events(client, auth["auditor"], event="session_expired")) == 1


def test_failed_login_is_audited(client, auth):
    r = client.post("/auth/login", json={"email": "operator@test.local", "password": "wrong-password"})
    assert r.status_code == 401
    rows = audit_events(client, auth["auditor"], event="login", outcome="failure")
    assert len(rows) == 1 and rows[0]["user_email"] == "operator@test.local"


def test_audit_log_is_immutable_at_db_level(client, auth):
    with client.session_factory() as s:
        with pytest.raises(Exception, match="append-only"):
            s.execute(text("update audit_log set outcome='tampered'"))
        s.rollback()
        with pytest.raises(Exception, match="append-only"):
            s.execute(text("delete from audit_log"))
        s.rollback()
        assert s.execute(text("select count(*) from audit_log")).scalar() > 0


def test_no_endpoint_mutates_audit_log(client, auth):
    h = auth["admin"]
    assert client.delete("/audit", headers=h).status_code == 405
    assert client.put("/audit", headers=h, json={}).status_code == 405
    assert client.patch("/audit/1", headers=h, json={}).status_code == 404


def test_audit_filters_and_export_hook(client, auth):
    from app import audit
    with client.session_factory() as s:
        from app.models import User
        u = s.query(User).filter_by(role="admin").one()
        audit.record_export(s, u, None, "reports", {"format": "xlsx"})
    rows = audit_events(client, auth["auditor"], event="export", module="reports")
    assert len(rows) == 1 and "xlsx" in rows[0]["detail"]


# ---------- golden path ----------
def test_golden_path(client, auth):
    op, rv, au = auth["operator"], auth["reviewer"], auth["auditor"]
    assert client.get("/health").json()["status"] == "ok"
    for mod, i in (("cases", 1), ("upload", 2)):
        client.post("/audit/module-events", headers=op,
                    json={"event": "module_enter", "module": mod, "client_event_id": f"golden-{i:04d}"})
    cid = new_case(client, op)
    r = upload(client, op, cid, make_png(seed=3))
    assert r.status_code == 201 and r.json()["qc_passed"] is True and r.json()["status"] == "image_uploaded"
    assert client.get(f"/cases/{cid}/image", headers=op).headers["content-type"] == "image/png"
    inf = client.post(f"/cases/{cid}/inference", headers=op).json()
    assert inf["status"] == "completed" and inf["is_demo"] is True
    hm = client.get(f"/cases/{cid}/inferences/{inf['id']}/heatmap", headers=rv)
    assert hm.status_code == 200 and hm.content.startswith(b"\x89PNG")
    rev = client.post(f"/cases/{cid}/reviews", headers=rv,
                      json={"agrees": True, "final_label": inf["label"], "comment": "ok"})
    assert rev.status_code == 201 and rev.json()["inference_id"] == inf["id"]
    assert len(client.get(f"/cases/{cid}/reviews", headers=au).json()) == 1
    client.post("/auth/logout", headers=op, json={"active_module": "upload", "client_event_id": "golden-0009"})
    events = [e["event"] for e in audit_events(client, au)]
    for expected in ("login", "module_enter", "case_created", "image_upload", "inference_run",
                     "review_created", "module_exit", "logout"):
        assert expected in events, expected
