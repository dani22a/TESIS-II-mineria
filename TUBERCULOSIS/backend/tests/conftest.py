"""Test fixtures.

DB: set TEST_DATABASE_URL (e.g. postgresql+psycopg://USER:PASS@localhost:5432/tb_test, a DISPOSABLE
database: tables are dropped/recreated per test). Without it, a temporary SQLite file is used.
"""
import io
import os

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import sessionmaker

from app import audit_guards
from app.config import settings
from app.db import Base, get_db, make_engine
from app.inference import InferenceEngine, get_engine
from app.main import app
from app.models import User
from app.security import hash_password

settings.bcrypt_rounds = 4  # fast hashing in tests
PASSWORD = "Test-Passw0rd!"
ROLES = ["admin", "operator", "reviewer", "auditor"]


@pytest.fixture(scope="session")
def engine(tmp_path_factory):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path_factory.mktemp('db') / 'test.db'}"
    eng = make_engine(url)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        audit_guards.install(conn)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        for role in ROLES:
            s.add(User(email=f"{role}@test.local", full_name=role.title(), role=role,
                       hashed_password=hash_password(PASSWORD)))
        s.commit()
    yield Session
    # no cleanup needed: next test drops/recreates


@pytest.fixture()
def client(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))

    def _get_db():
        with db_session() as s:
            yield s

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        c.session_factory = db_session
        yield c
    app.dependency_overrides.clear()


def login(client, role: str) -> dict:
    r = client.post("/auth/login", json={"email": f"{role}@test.local", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    return {role: login(client, role) for role in ROLES}


def make_png(size: int = 512, uniform: bool = False, seed: int = 1) -> bytes:
    rng = np.random.default_rng(seed)
    arr = np.full((size, size), 100, np.uint8) if uniform else rng.integers(0, 256, (size, size), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


class FailingEngine(InferenceEngine):
    model_version = "failing-0"
    is_demo = True

    def predict(self, image_bytes):
        raise RuntimeError("model crashed")


@pytest.fixture()
def failing_engine():
    app.dependency_overrides[get_engine] = lambda: FailingEngine()
    yield
    app.dependency_overrides.pop(get_engine, None)
