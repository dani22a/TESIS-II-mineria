"""End-to-end golden-path smoke test against a LIVE server (real HTTP, not TestClient).

Usage (from TUBERCULOSIS/backend, with its requirements installed):
    python ../scripts/e2e_smoke.py --spawn            # temp SQLite DB, migrate, seed, run uvicorn, test, stop
    python ../scripts/e2e_smoke.py --base-url http://localhost:8000   # against an already running server

Exit code 0 only if every check passes.
"""
import argparse
import io
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import numpy as np
from PIL import Image

PASSWORD = os.environ.get("SEED_PASSWORD", "Demo-Passw0rd!")
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def png_bytes(size: int = 512, seed: int = 7) -> bytes:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size]
    arr = (90 + 80 * np.exp(-((x - size / 2) ** 2 + (y - size / 2) ** 2) / (2 * 150.0**2))
           + rng.normal(0, 20, (size, size))).clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def login(c: httpx.Client, email: str) -> dict:
    r = c.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def run(base: str) -> None:
    c = httpx.Client(base_url=base, timeout=60)
    h = c.get("/health")
    check("health", h.status_code == 200 and h.json().get("demo_mode") is True, h.text)

    op = login(c, "operator@demo.local")
    check("login operator", True)
    rv = login(c, "reviewer@demo.local")
    ad = login(c, "admin@demo.local")
    au = login(c, "auditor@demo.local")
    bad = c.post("/auth/login", json={"email": "operator@demo.local", "password": "wrong-password"})
    check("bad login rejected", bad.status_code == 401, str(bad.status_code))

    for module in ("cases", "upload"):
        r = c.post("/audit/module-events", headers=op,
                   json={"event": "module_enter", "module": module, "client_event_id": f"e2e-enter-{module}-1"})
        check(f"module_enter {module}", r.status_code == 201, str(r.status_code))
    r = c.post("/audit/module-events", headers=op,
               json={"event": "module_exit", "module": "upload", "client_event_id": "e2e-exit-upload-1"})
    check("module_exit upload", r.status_code == 201, str(r.status_code))

    r = c.post("/cases", headers=op, json={"institution": "E2E Hospital", "notes": "e2e golden path"})
    check("create case", r.status_code == 201, r.text[:120])
    case = r.json()
    cid = case["id"]

    r = c.post(f"/cases/{cid}/image", headers=op, files={"file": ("bad.txt", b"not an image", "text/plain")})
    check("invalid file rejected", r.status_code in (400, 415, 422), f"{r.status_code} {r.text[:100]}")
    r = c.post(f"/cases/{cid}/image", headers=op, files={"file": ("xray.png", png_bytes(), "image/png")})
    check("upload PNG", r.status_code == 201 and r.json().get("has_image"), f"{r.status_code} qc_passed={r.json().get('qc_passed')}")

    r = c.post(f"/cases/{cid}/inference", headers=op)
    inf = r.json()
    check("demo inference", r.status_code == 201 and inf.get("is_demo") is True and inf.get("model_version") == "demo-0",
          f"status={inf.get('status')} label={inf.get('label')} score={inf.get('score')} is_demo={inf.get('is_demo')}")

    r = c.post(f"/cases/{cid}/reviews", headers=op,
               json={"agrees": True, "final_label": "no_compatible_findings"})
    check("operator cannot review (403)", r.status_code == 403, str(r.status_code))
    r = c.post(f"/cases/{cid}/reviews", headers=rv,
               json={"agrees": True, "final_label": inf.get("label") or "not_evaluable", "comment": "e2e"})
    check("reviewer evaluation", r.status_code == 201, r.text[:120])

    r = c.get("/dashboard/summary", headers=ad)
    check("dashboard summary", r.status_code == 200 and r.json().get("is_demo") is True,
          f"total_cases={r.json().get('operational', {}).get('total_cases')}")

    for fmt in ("pdf", "docx", "xlsx"):
        r = c.get(f"/reports/management.{fmt}", headers=ad)
        body = r.content
        ok = r.status_code == 200 and len(body) > 500
        detail = f"{len(body)} bytes"
        if ok:
            try:
                if fmt == "pdf":
                    from pypdf import PdfReader
                    rd = PdfReader(io.BytesIO(body))
                    text = " ".join((p.extract_text() or "") for p in rd.pages)
                    ok = len(rd.pages) >= 1 and "demo" in text.lower()
                    detail += f", {len(rd.pages)} page(s), demo flag in text={'demo' in text.lower()}"
                elif fmt == "docx":
                    import docx
                    d = docx.Document(io.BytesIO(body))
                    text = " ".join(p.text for p in d.paragraphs)
                    ok = len(d.paragraphs) > 0 and "demo" in text.lower()
                    detail += f", {len(d.paragraphs)} paragraphs, {len(d.tables)} tables"
                else:
                    import openpyxl
                    wb = openpyxl.load_workbook(io.BytesIO(body))
                    ok = len(wb.sheetnames) >= 1
                    detail += f", sheets={wb.sheetnames}"
            except Exception as e:  # noqa: BLE001
                ok, detail = False, f"cannot open: {e}"
        check(f"export {fmt}", ok, detail)

    r = c.get("/reports/management.pdf", headers=op)
    check("operator cannot export (403)", r.status_code == 403, str(r.status_code))

    r = c.get("/audit", headers=au, params={"limit": 500})
    check("auditor reads audit", r.status_code == 200, str(r.status_code))
    events = r.json()
    seen = {(e["event"], e["module"]) for e in events}
    for ev in (("login", "auth"), ("module_enter", "cases"), ("module_exit", "upload"), ("export", "reports"),
               ("case_created", "cases"), ("review_created", "review")):
        check(f"audit has {ev[0]}/{ev[1]}", ev in seen)
    check("operator cannot read audit (403)", c.get("/audit", headers=op).status_code == 403)

    out = c.post("/auth/logout", headers=op, json={"active_module": "cases", "client_event_id": "e2e-logout-1"})
    check("logout", out.status_code == 204, str(out.status_code))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def spawn_and_run() -> None:
    backend = Path(__file__).resolve().parent.parent / "backend"
    tmp = tempfile.mkdtemp(prefix="tb_e2e_")
    db = Path(tmp, "e2e.db").as_posix()
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}", "STORAGE_DIR": Path(tmp, "storage").as_posix(),
           "CORS_ORIGINS": "http://localhost:5173", "BCRYPT_ROUNDS": "4", "PYTHONUTF8": "1"}
    for cmd in ([sys.executable, "-m", "alembic", "upgrade", "head"], [sys.executable, "-m", "app.seed"]):
        subprocess.run(cmd, cwd=backend, env=env, check=True)
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
                           cwd=backend, env=env)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if httpx.get(base + "/health", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.5)
        else:
            raise SystemExit("server did not start")
        print(f"server up at {base} (db {db})")
        run(base)
    finally:
        srv.terminate()
        try:
            srv.wait(10)
        except subprocess.TimeoutExpired:
            srv.kill()
        print("server stopped")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url")
    ap.add_argument("--spawn", action="store_true", help="start a temp SQLite server on a free port")
    a = ap.parse_args()
    if a.spawn:
        spawn_and_run()
    elif a.base_url:
        run(a.base_url)
    else:
        ap.error("pass --spawn or --base-url")
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
