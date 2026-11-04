from fastapi.testclient import TestClient

from app.main import app, fetch_summary

SUMMARY = {
    "is_demo": True, "demo_notice": "DEMO",
    "operational": {"total_cases": 5, "cases_by_status": {"completed": 3, "technical_failure": 2},
                    "results_by_outcome": {"probable_tuberculosis": 1}, "technical_failures": 2,
                    "not_evaluable": 0, "reviews": {"total": 1, "agreed": 1, "disagreed": 0},
                    "processing_seconds": {"n": 3, "mean": 0.1, "median": 0.1, "max": 0.2},
                    "inferences_by_model_version": {"demo-0": 3},
                    "case_ids": [1, 2], "patient_name": "LEAK"},  # must never be forwarded
    "scientific": {"available": False, "reason": "No reference labels"},
}


def client():
    app.dependency_overrides[fetch_summary] = lambda: SUMMARY
    return TestClient(app)


def test_query_without_llm_is_templated_and_aggregate_only(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client().post("/query", json={"question": "How many technical failures?"}).json()
    assert r["mode"] == "template" and "2 of 5" in r["answer"] and "DEMO MODE" in r["answer"]
    assert "LEAK" not in str(r) and "case_ids" not in str(r)


def test_query_performance_not_available_without_labels(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client().post("/query", json={"question": "What is the sensitivity?"}).json()
    assert "not available" in r["answer"]


def test_rag_returns_sources_and_insufficient_evidence():
    c = TestClient(app)
    ok = c.post("/rag", json={"question": "Is chest X-ray recommended for TB screening?"}).json()
    assert ok["sufficient"] and ok["sources"][0]["source"].endswith(".md")
    no = c.post("/rag", json={"question": "What is the capital of France?"}).json()
    assert no["sufficient"] is False and no["sources"] == [] and "Insufficient evidence" in no["answer"]
