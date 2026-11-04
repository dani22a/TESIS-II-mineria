import io

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

from .conftest import make_png
from .test_api import audit_events, new_case, upload


def seed(client, auth):
    h = auth["operator"]
    for seed_ in (1, 2):  # two completed
        cid = new_case(client, h)
        upload(client, h, cid, make_png(seed=seed_))
        assert client.post(f"/cases/{cid}/inference", headers=h).status_code == 201
    cid = new_case(client, h)  # one not evaluable
    upload(client, h, cid, make_png(uniform=True))
    client.post(f"/cases/{cid}/inference", headers=h)
    new_case(client, h)  # one created


def test_summary_counts_filters_and_scientific_block(client, auth):
    seed(client, auth)
    s = client.get("/dashboard/summary", headers=auth["operator"]).json()
    assert s["operational"]["total_cases"] == 4
    assert s["operational"]["cases_by_status"]["completed"] == 2
    assert s["is_demo"] is True and s["demo_notice"]
    assert s["scientific"]["available"] is False and s["scientific"]["reason"]
    h = auth["auditor"]
    f = client.get("/dashboard/summary", headers=h, params={"status": "completed"}).json()
    assert f["operational"]["total_cases"] == 2
    f = client.get("/dashboard/summary", headers=h, params={"model_version": "nope"}).json()
    assert f["operational"]["total_cases"] == 0
    f = client.get("/dashboard/summary", headers=h, params={"date_from": "2999-01-01T00:00:00"}).json()
    assert f["operational"]["total_cases"] == 0


def test_exports_parse_back_with_consistent_counts(client, auth):
    seed(client, auth)
    h = auth["auditor"]
    for kind in ("operational", "management"):
        r = client.get(f"/reports/{kind}.pdf", headers=h, params={"status": "completed"})
        assert r.status_code == 200 and r.content.startswith(b"%PDF")
        text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
        assert "DEMO MODE" in text and "Total cases" in text and "Scientific metrics" in text
        r = client.get(f"/reports/{kind}.docx", headers=h, params={"status": "completed"})
        doc = Document(io.BytesIO(r.content))
        cells = [c.text for t in doc.tables for row in t.rows for c in row.cells]
        assert cells[cells.index("Total cases") + 1] == "2"
        assert any("DEMO MODE" in p.text for p in doc.paragraphs)
        r = client.get(f"/reports/{kind}.xlsx", headers=h, params={"status": "completed"})
        ws = load_workbook(io.BytesIO(r.content)).active
        vals = {row[0].value: row[1].value for row in ws.iter_rows() if len(row) > 1}
        assert vals["Total cases"] == 2
    full = load_workbook(io.BytesIO(client.get("/reports/operational.xlsx", headers=h).content)).active
    assert {r[0].value: r[1].value for r in full.iter_rows()}["Total cases"] == 4


def test_operator_cannot_export_and_exports_are_audited(client, auth):
    seed(client, auth)
    assert client.get("/reports/operational.pdf", headers=auth["operator"]).status_code == 403
    assert client.get("/reports/operational.csv", headers=auth["admin"]).status_code in (404, 422)
    for role in ("admin", "reviewer", "auditor"):
        assert client.get("/reports/management.xlsx", headers=auth[role]).status_code == 200
    ev = audit_events(client, auth["auditor"], event="export")
    assert len(ev) == 3 and all(e["module"] == "reports" for e in ev)
    assert '"management"' in ev[0]["detail"]
