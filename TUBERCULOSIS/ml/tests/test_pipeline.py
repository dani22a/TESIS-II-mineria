import numpy as np
import pandas as pd
import pytest

from tbml import metrics as M
from tbml.splits import LeakageError, assert_no_leakage, grouped_kfold, split_manifest


def manifest(n_patients=60, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_patients):
        label = int(rng.random() < 0.4)
        for k in range(rng.integers(1, 4)):  # several images per patient
            rows.append({"image_id": f"p{p}_{k}", "patient_id": f"p{p}", "label": label,
                         "institution": f"i{p % 3}" if p < 48 else "ext", "sha256": f"h{p}_{k}"})
    return pd.DataFrame(rows)


def test_splits_have_no_patient_leakage_and_external_is_separate():
    s = split_manifest(manifest(), seed=1, external_institutions=("ext",))
    assert set(s) == {"train", "val", "test", "external"}
    ids = {k: set(v.patient_id) for k, v in s.items()}
    for a in ids:
        for b in ids:
            if a < b:
                assert not ids[a] & ids[b], (a, b)
    assert set(s["external"].institution) == {"ext"}
    assert "ext" not in set(pd.concat([s["train"], s["val"], s["test"]]).institution)


def test_leakage_assertion_detects_shared_patient_and_duplicate_image():
    df = manifest()
    with pytest.raises(LeakageError):
        assert_no_leakage({"a": df[df.patient_id == "p1"], "b": df[df.patient_id == "p1"]})
    a, b = df[df.patient_id == "p1"].copy(), df[df.patient_id == "p2"].copy()
    b["sha256"] = a["sha256"].iloc[0]
    with pytest.raises(LeakageError):
        assert_no_leakage({"a": a, "b": b})


def test_grouped_kfold_is_patient_disjoint():
    for _, tr, va in grouped_kfold(manifest(), 4):
        assert not set(tr.patient_id) & set(va.patient_id)


def test_metrics_known_values():
    y = np.array([1, 1, 0, 0, 1, 0])
    p = np.array([0.9, 0.4, 0.2, 0.6, 0.8, 0.1])
    m = M.all_metrics(y, p, 0.5)
    assert (m["tp"], m["fn"], m["fp"], m["tn"]) == (2, 1, 1, 2)
    assert m["sensitivity"] == pytest.approx(2 / 3) and m["specificity"] == pytest.approx(2 / 3)
    from sklearn.metrics import roc_auc_score
    assert m["auc_roc"] == pytest.approx(roc_auc_score(y, p))


def test_grouped_bootstrap_ci_brackets_point_and_is_deterministic():
    df = manifest(80)
    df["prob"] = np.clip(df.label * 0.6 + np.random.default_rng(1).normal(0.2, 0.25, len(df)), 0, 1)
    f = lambda d: M.all_metrics(d.label, d.prob, 0.5)["auc_roc"]
    a = M.grouped_bootstrap_ci(df, f, n_boot=200, seed=3)
    b = M.grouped_bootstrap_ci(df, f, n_boot=200, seed=3)
    assert a == b and a["lo"] <= a["point"] <= a["hi"] and a["lo"] < a["hi"]


def test_delong_matches_identical_scores_and_detects_difference():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 300)
    good = y + rng.normal(0, 0.6, 300)
    noise = rng.normal(0, 1, 300)
    same = M.delong_test(y, good, good + 1e-9 * rng.normal(size=300))
    diff = M.delong_test(y, good, noise)
    assert diff["auc_a"] > diff["auc_b"] and diff["p"] < 0.001
    assert same["p"] != same["p"] or same["p"] > 0.5  # NaN (zero variance) or not significant


def test_mcnemar_and_holm():
    y = np.array([1] * 10 + [0] * 10)
    a = y.copy()
    b = y.copy(); b[:8] = 0  # B wrong on 8 positives that A gets right
    r = M.mcnemar_exact(y, a, b)
    assert (r["a_only_correct"], r["b_only_correct"]) == (8, 0) and r["p"] == pytest.approx(2 * 0.5 ** 8)
    assert M.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_friedman_requires_proper_blocks():
    cv = pd.DataFrame({"model": ["a", "b", "c"] * 2, "block": [0, 0, 0, 1, 1, 1], "auc_roc": [.9, .8, .7] * 2})
    assert M.friedman_wilcoxon(cv)["applicable"] is False  # 2 blocks only
    rng = np.random.default_rng(0)
    rows = [{"model": m, "block": b, "auc_roc": 0.9 - 0.05 * i + 0.01 * rng.normal()}
            for b in range(8) for i, m in enumerate("abc")]
    r = M.friedman_wilcoxon(pd.DataFrame(rows))
    assert r["applicable"] and r["friedman_p"] < 0.05 and len(r["wilcoxon"]) == 3
