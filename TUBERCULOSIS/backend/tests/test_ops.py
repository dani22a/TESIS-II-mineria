from app.service_token import issue

from .conftest import make_png
from .test_api import audit_events, new_case, upload


def service_headers(client):
    with client.session_factory() as s:
        return {"Authorization": f"Bearer {issue(s, 1)}"}


def test_service_account_scope(client, auth):
    h = service_headers(client)
    assert client.get("/cases", headers=h).status_code == 200
    assert client.get("/dashboard/summary", headers=h).status_code == 200
    # no review, no user management
    assert client.get("/users", headers=h).status_code == 403
    assert client.post("/cases/1/reviews", headers=h,
                       json={"agrees": True, "final_label": "not_evaluable"}).status_code == 403


def test_pending_review_and_qc(client, auth):
    op = auth["operator"]
    a = new_case(client, op)
    upload(client, op, a, make_png(seed=1))
    client.post(f"/cases/{a}/inference", headers=op)
    b = new_case(client, op)
    upload(client, op, b, make_png(seed=1))  # duplicate image of a
    new_case(client, op)                     # no image
    c = new_case(client, op)
    upload(client, op, c, make_png(uniform=True))  # fails QC
    pend = client.get("/ops/pending-review", headers=op).json()
    assert pend["count"] == 1 and pend["items"][0]["case_id"] == a
    client.post(f"/cases/{a}/reviews", headers=auth["reviewer"],
                json={"agrees": True, "final_label": "no_compatible_findings"})
    assert client.get("/ops/pending-review", headers=op).json()["count"] == 0
    qc = client.get("/ops/qc", headers=op).json()
    assert qc["duplicates"][0]["case_ids"] == [a, b]
    assert len(qc["missing_image"]) == 1 and qc["invalid"][0]["case_id"] == c
    assert "sha256_prefix" in qc["duplicates"][0] and "image_sha256" not in str(qc)


def test_ops_events_audited_and_role_checked(client, auth):
    body = {"workflow": "WF-04", "event": "alert_sent", "detail": {"count": 2}}
    assert client.post("/ops/events", json=body, headers=auth["operator"]).status_code == 403
    h = service_headers(client)
    assert client.post("/ops/events", json=body, headers=h).status_code == 201
    assert "wf_alert_sent" in [e["event"] for e in audit_events(client, auth["auditor"])]
