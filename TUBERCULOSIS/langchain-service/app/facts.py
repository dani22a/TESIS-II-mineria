"""Whitelist of AGGREGATE facts taken from the backend dashboard summary.

Nothing else from the summary is ever forwarded (no case ids, no pseudonyms, no images).
"""


def extract_facts(summary: dict) -> dict:
    op = summary.get("operational", {})
    sci = summary.get("scientific", {})
    return {
        "is_demo": bool(summary.get("is_demo")),
        "demo_notice": summary.get("demo_notice"),
        "total_cases": op.get("total_cases", 0),
        "cases_by_status": dict(op.get("cases_by_status", {})),
        "results_by_outcome": dict(op.get("results_by_outcome", {})),
        "inferences_by_model_version": dict(op.get("inferences_by_model_version", {})),
        "processing_seconds": dict(op.get("processing_seconds", {})),
        "technical_failures": op.get("technical_failures", 0),
        "not_evaluable": op.get("not_evaluable", 0),
        "reviews": dict(op.get("reviews", {})),
        "scientific_available": bool(sci.get("available")),
        "scientific_reason": sci.get("reason"),
    }


def templated_answer(question: str, f: dict) -> str:
    """Deterministic answer from aggregates; used when no LLM is configured."""
    q = question.lower()
    demo = " (DEMO MODE: not a validated model)" if f["is_demo"] else ""
    st = f["cases_by_status"]
    if any(k in q for k in ("sensitiv", "specific", "accuracy", "auc", "performance", "precision")):
        if not f["scientific_available"]:
            return "Performance metrics are not available: " + (f["scientific_reason"] or "no reference labels") + demo
        return "Performance metrics are available in the scientific block of the dashboard." + demo
    if any(k in q for k in ("fail", "error")):
        return f"Technical failures: {f['technical_failures']} of {f['total_cases']} cases." + demo
    if "evaluable" in q or "quality" in q:
        return f"Not evaluable cases (failed image QC): {f['not_evaluable']} of {f['total_cases']}." + demo
    if "review" in q:
        r = f["reviews"]
        return (f"Reviews: {r.get('total', 0)} total, {r.get('agreed', 0)} agreed with the system, "
                f"{r.get('disagreed', 0)} disagreed. Agreement is operational, not ground truth." + demo)
    if any(k in q for k in ("time", "second", "latency", "speed")):
        p = f["processing_seconds"]
        return (f"Processing time (n={p.get('n', 0)}): mean {p.get('mean')} s, median {p.get('median')} s, "
                f"max {p.get('max')} s." + demo)
    if any(k in q for k in ("result", "outcome", "positive", "probable", "label")):
        return f"Results by outcome: {f['results_by_outcome'] or 'none yet'}." + demo
    parts = ", ".join(f"{k}: {v}" for k, v in st.items() if v)
    return (f"Total cases: {f['total_cases']}. By status: {parts or 'none'}. "
            f"Results: {f['results_by_outcome'] or 'none'}." + demo)
