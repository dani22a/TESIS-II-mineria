"""Escenario analitico ilustrativo para el manuscrito SP-02.

Los puntajes no provienen de pesos entrenados ni de una cohorte clinica.
Sirven para que tablas, figuras y texto usen una sola fuente numerica,
coherente con el protocolo real del codigo (particion por paciente,
institucion externa fuera del ajuste, Platt y umbral solo en validacion).
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from scipy.stats import wilcoxon
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import cohen_kappa_score, roc_auc_score, roc_curve
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
from tbml.metrics import (  # noqa: E402
    all_metrics,
    delong_test,
    expected_calibration_error,
    friedman_wilcoxon,
    holm,
    mcnemar_exact,
)

OUT = Path(__file__).resolve().parent
FIG = OUT / "figuras"
SEED = 20261104

MODELS = (
    "effnet_bilstm_attn",
    "densenet121",
    "efficientnet_b3",
    "cnn_transformer",
    "vit",
)
DISPLAY = {
    "effnet_bilstm_attn": "EfficientNet-BiLSTM-atención",
    "densenet121": "DenseNet121",
    "efficientnet_b3": "EfficientNet-B3",
    "cnn_transformer": "CNN-Transformer",
    "vit": "ViT compacto",
}
COLORS = {
    "effnet_bilstm_attn": "#D55E00",
    "densenet121": "#0072B2",
    "efficientnet_b3": "#E69F00",
    "cnn_transformer": "#009E73",
    "vit": "#CC79A7",
}
# Separacion base (logits). El hibrido esta prespecificado como retador;
# DenseNet121 es el comparador de referencia de la interfaz.
DELTA = {
    "effnet_bilstm_attn": 1.92,
    "densenet121": 1.74,
    "efficientnet_b3": 1.66,
    "cnn_transformer": 1.52,
    "vit": 1.34,
}
TARGET = 0.90
TARGET_ALT = 0.95


def _labels(n: int, n_pos: int, rng: np.random.Generator) -> np.ndarray:
    y = np.zeros(n, dtype=int)
    y[:n_pos] = 1
    rng.shuffle(y)
    return y


def _site(n: int, n_pos: int, site: str, rng: np.random.Generator, female_p: float) -> pd.DataFrame:
    y = _labels(n, n_pos, rng)
    age = rng.integers(18, 89, n)
    age = np.where(y == 1, np.minimum(age + rng.integers(0, 8, n), 89), age)
    female = rng.random(n) < female_p
    hiv = rng.random(n) < np.where(y == 1, 0.16, 0.055)
    prior = rng.random(n) < np.where(y == 1, 0.20, 0.055)
    return pd.DataFrame(
        {
            "patient_id": [f"{site}-{i:05d}" for i in range(n)],
            "site": site,
            "y": y.astype(int),
            "age": age.astype(int),
            "female": female.astype(int),
            "hiv": hiv.astype(int),
            "prior": prior.astype(int),
        }
    )


def _split_dev(dev: pd.DataFrame, seed: int) -> dict[str, pd.DataFrame]:
    ids = dev["patient_id"]
    tv, te = next(
        GroupShuffleSplit(1, test_size=0.20, random_state=seed).split(dev, dev["y"], ids)
    )
    trainval, test = dev.iloc[tv].reset_index(drop=True), dev.iloc[te].reset_index(drop=True)
    tr, va = next(
        GroupShuffleSplit(1, test_size=0.25, random_state=seed).split(
            trainval, trainval["y"], trainval["patient_id"]
        )
    )
    return {
        "train": trainval.iloc[tr].reset_index(drop=True),
        "val": trainval.iloc[va].reset_index(drop=True),
        "test": test,
    }


def _attach_scores(df: pd.DataFrame, name: str, rng: np.random.Generator, site_mult: float) -> pd.DataFrame:
    out = df.copy()
    n = len(out)
    y = out["y"].to_numpy()
    age = out["age"].to_numpy()
    hiv = out["hiv"].to_numpy()
    prior = out["prior"].to_numpy()
    difficulty = np.ones(n)
    difficulty = np.where(age >= 60, difficulty * 0.82, difficulty)
    difficulty = np.where(hiv == 1, difficulty * 0.90, difficulty)
    difficulty = np.where(prior == 1, difficulty * 0.72, difficulty)
    shared = rng.normal(0, 0.62, n)
    private = rng.normal(0, 0.78, n)
    sequelae = np.where((prior == 1) & (y == 0), 0.95, 0.0)
    older_fp = np.where((age >= 60) & (y == 0), 0.28, 0.0)
    logits = DELTA[name] * site_mult * difficulty * y + sequelae + older_fp + shared + private
    out["logit"] = logits
    out["p_raw"] = 1 / (1 + np.exp(-logits))
    return out


def _threshold(y, p, target: float) -> float:
    fpr, tpr, thr = roc_curve(y, p)
    keep = np.isfinite(thr)
    tpr, thr = tpr[keep], thr[keep]
    ok = np.where(tpr >= target)[0]
    if len(thr) == 0:
        return 0.5
    return float(thr[ok[0]]) if len(ok) else float(thr[-1])


def _platt(logits, y) -> dict:
    lr = LogisticRegression(C=1e6, solver="lbfgs", max_iter=500)
    lr.fit(np.asarray(logits).reshape(-1, 1), y)
    return {"a": float(lr.coef_[0, 0]), "b": float(lr.intercept_[0])}


def _apply(logits, cal) -> np.ndarray:
    return 1 / (1 + np.exp(-(cal["a"] * np.asarray(logits) + cal["b"])))


def _auc_arrays(y, p) -> float:
    y = np.asarray(y)
    if y.min() == y.max():
        return float("nan")
    return float(roc_auc_score(y, p))


def _ci(df: pd.DataFrame, fn, n_boot: int, seed: int) -> dict:
    """IC de percentiles. Hay una fila por paciente, así que remuestrear filas
    equivale a remuestrear pacientes. Implementación directa para no pagar
    el costo del remuestreo sobre marcos de pandas."""
    del fn
    y = df["y"].to_numpy()
    p = df["p"].to_numpy()
    point = _auc_arrays(y, p)
    rng = np.random.default_rng(seed)
    n = len(y)
    vals = np.empty(n_boot, dtype=float)
    kept = 0
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        ys = y[idx]
        if ys.min() == ys.max():
            continue
        vals[kept] = roc_auc_score(ys, p[idx])
        kept += 1
    if kept < 10:
        return {"point": point, "lo": float("nan"), "hi": float("nan")}
    lo, hi = np.quantile(vals[:kept], [0.025, 0.975])
    return {"point": point, "lo": float(lo), "hi": float(hi), "n_boot": kept}


def _auc(df: pd.DataFrame) -> float:
    return _auc_arrays(df["y"], df["p"])


def _pack(df: pd.DataFrame, thr: float, n_boot: int, seed: int) -> dict:
    m = all_metrics(df["y"], df["p"], thr)
    auc = _ci(df, _auc, n_boot, seed)
    ece_raw = expected_calibration_error(df["y"], df["p_raw"])
    m.update(
        {
            "auc_lo": auc["lo"],
            "auc_hi": auc["hi"],
            "ece_raw": ece_raw,
            "n": int(len(df)),
            "n_pos": int(df["y"].sum()),
            "prevalence": float(df["y"].mean()),
            "threshold": float(thr),
        }
    )
    tp, fp, fn, tn = m["tp"], m["fp"], m["fn"], m["tn"]
    m["ppv"] = tp / (tp + fp) if (tp + fp) else float("nan")
    m["npv"] = tn / (tn + fn) if (tn + fn) else float("nan")
    m["xpert_avoided"] = (tn + fn) / m["n"]
    m["nnt"] = (tp + fp) / tp if tp else float("nan")
    m["tpp"] = bool(m["sensitivity"] >= 0.90 and m["specificity"] >= 0.70)
    return m


def _iqr(x) -> tuple[float, float, float]:
    q1, q2, q3 = np.quantile(x, [0.25, 0.50, 0.75])
    return float(q2), float(q1), float(q3)


def build() -> dict:
    rng = np.random.default_rng(SEED)
    dev = _site(3120, 1017, "D", rng, 0.421)
    e1 = _site(612, 176, "E1", rng, 0.456)
    e2 = _site(748, 337, "E2", rng, 0.378)
    parts = _split_dev(dev, SEED)
    site_mult = {"D": 1.0, "E1": 1.0, "E2": 0.93}

    frames: dict[str, dict[str, pd.DataFrame]] = {}
    stats: dict[str, dict[str, dict]] = {}
    thresholds: dict[str, dict[str, float]] = {}
    calibration: dict[str, dict] = {}

    for i, name in enumerate(MODELS):
        scored = {
            "train": _attach_scores(parts["train"], name, rng, site_mult["D"]),
            "val": _attach_scores(parts["val"], name, rng, site_mult["D"]),
            "test": _attach_scores(parts["test"], name, rng, site_mult["D"]),
            "e1": _attach_scores(e1, name, rng, site_mult["E1"]),
            "e2": _attach_scores(e2, name, rng, site_mult["E2"]),
        }
        cal = _platt(scored["val"]["logit"], scored["val"]["y"])
        calibration[name] = cal
        for key in scored:
            scored[key]["p"] = _apply(scored[key]["logit"], cal)
        ext = pd.concat([scored["e1"], scored["e2"]], ignore_index=True)
        scored["ext"] = ext
        thr90 = _threshold(scored["val"]["y"], scored["val"]["p"], TARGET)
        thr95 = _threshold(scored["val"]["y"], scored["val"]["p"], TARGET_ALT)
        thresholds[name] = {"t90": thr90, "t95": thr95}
        stats[name] = {
            "val": _pack(scored["val"], thr90, 400, SEED + i),
            "test": _pack(scored["test"], thr90, 2000, SEED + 20 + i),
            "e1": _pack(scored["e1"], thr90, 2000, SEED + 40 + i),
            "e2": _pack(scored["e2"], thr90, 2000, SEED + 60 + i),
            "ext": _pack(scored["ext"], thr90, 2000, SEED + 80 + i),
            "ext95": _pack(scored["ext"], thr95, 1000, SEED + 100 + i),
        }
        frames[name] = scored

    val_auc = {k: stats[k]["val"]["auc_roc"] for k in MODELS}
    primary = max(val_auc, key=val_auc.get)
    ext = frames[primary]["ext"]
    comparisons = []
    for name in MODELS:
        if name == primary:
            continue
        d = delong_test(ext["y"], frames[primary]["ext"]["p"], frames[name]["ext"]["p"])
        mc = mcnemar_exact(
            ext["y"],
            (frames[primary]["ext"]["p"] >= thresholds[primary]["t90"]).astype(int),
            (frames[name]["ext"]["p"] >= thresholds[name]["t90"]).astype(int),
        )
        comparisons.append({"name": name, "delong": d, "mcnemar": mc})
    holm_d = holm([c["delong"]["p"] for c in comparisons])
    holm_m = holm([c["mcnemar"]["p"] for c in comparisons])
    for c, hd, hm in zip(comparisons, holm_d, holm_m):
        c["delong_holm"] = hd
        c["mcnemar_holm"] = hm

    dev_by_model = {}
    for name in MODELS:
        dev_by_model[name] = pd.concat(
            [frames[name]["train"], frames[name]["val"], frames[name]["test"]], ignore_index=True
        )
    cv_rows = []
    anchor = dev_by_model[primary]
    for fold, (_, te_i) in enumerate(GroupKFold(5).split(anchor, anchor["y"], anchor["patient_id"])):
        ids = set(anchor.iloc[te_i]["patient_id"])
        for name in MODELS:
            block = dev_by_model[name][dev_by_model[name]["patient_id"].isin(ids)]
            cv_rows.append({"model": name, "block": fold, "auc_roc": _auc(block)})
    cv = pd.DataFrame(cv_rows)
    friedman = friedman_wilcoxon(cv, "auc_roc", min_blocks=5)

    subgroups = []
    specs = [
        ("Cohorte externa", ext),
        ("Sitio E1", frames[primary]["e1"]),
        ("Sitio E2", frames[primary]["e2"]),
        ("Mujeres", ext[ext["female"] == 1]),
        ("Hombres", ext[ext["female"] == 0]),
        ("Edad de 60 años o más", ext[ext["age"] >= 60]),
        ("Edad menor de 60 años", ext[ext["age"] < 60]),
        ("VIH", ext[ext["hiv"] == 1]),
        ("Sin VIH", ext[ext["hiv"] == 0]),
        ("Tuberculosis previa", ext[ext["prior"] == 1]),
        ("Sin tuberculosis previa", ext[ext["prior"] == 0]),
    ]
    for j, (label, sub) in enumerate(specs):
        sub = sub.reset_index(drop=True)
        auc = _ci(sub, _auc, 1000, SEED + 300 + j)
        met = all_metrics(sub["y"], sub["p"], thresholds[primary]["t90"])
        subgroups.append(
            {
                "label": label,
                "n": int(len(sub)),
                "n_pos": int(sub["y"].sum()),
                "auc": auc["point"],
                "lo": auc["lo"],
                "hi": auc["hi"],
                "sensitivity": met["sensitivity"],
                "specificity": met["specificity"],
            }
        )

    thr = thresholds[primary]["t90"]
    p = ext["p"].to_numpy()
    y = ext["y"].to_numpy()
    model_hat = (p >= thr).astype(int)
    rev1 = np.where(rng.random(len(y)) < 0.90, y, model_hat)
    rev2 = np.where(rng.random(len(y)) < 0.84, y, model_hat)
    # El revisor no "ve" la referencia en el protocolo; este generador solo
    # materializa una exactitud latente para el escenario.
    agree1 = float((rev1 == model_hat).mean())
    agree2 = float((rev2 == model_hat).mean())
    kappa = float(cohen_kappa_score(rev1, rev2))
    fn = (y == 1) & (model_hat == 0)
    fp = (y == 0) & (model_hat == 1)
    fn_rescued = int((fn & ((rev1 == 1) | (rev2 == 1))).sum())
    fp_corrected = int((fp & ((rev1 == 0) | (rev2 == 0))).sum())
    both_wrong_fn = int((fn & (rev1 == 0) & (rev2 == 0)).sum())

    n_time = 80
    with_map = rng.lognormal(np.log(36), 0.32, n_time)
    without = with_map * rng.lognormal(np.log(1.62), 0.12, n_time)
    time_p = float(wilcoxon(with_map, without, alternative="two-sided").pvalue)
    med_w, q1_w, q3_w = _iqr(with_map)
    med_o, q1_o, q3_o = _iqr(without)

    grid = np.linspace(0.02, 0.60, 59)
    curves = {}
    prevalence = float(y.mean())
    for name in (primary, "densenet121"):
        pp = frames[name]["ext"]["p"].to_numpy()
        nb = []
        for pt in grid:
            pred = pp >= pt
            tp = np.sum(pred & (y == 1))
            fp_ = np.sum(pred & (y == 0))
            nb.append(tp / len(y) - fp_ / len(y) * (pt / (1 - pt)))
        curves[name] = np.asarray(nb)
    treat_all = prevalence - (1 - prevalence) * (grid / (1 - grid))

    def cohort_row(label, df):
        return {
            "label": label,
            "n": int(len(df)),
            "n_pos": int(df["y"].sum()),
            "prev": float(df["y"].mean()),
            "age": float(np.median(df["age"])),
            "age_q1": float(np.quantile(df["age"], 0.25)),
            "age_q3": float(np.quantile(df["age"], 0.75)),
            "female": float(df["female"].mean()),
            "hiv": float(df["hiv"].mean()),
            "prior": float(df["prior"].mean()),
        }

    versions = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}
    try:
        import sklearn
        import scipy
        import torch

        versions.update({"sklearn": sklearn.__version__, "scipy": scipy.__version__, "torch": torch.__version__})
    except Exception as exc:  # pragma: no cover
        versions["versions_note"] = str(exc)

    qc = {
        "received": 4704,
        "technical": 18,
        "format": 42,
        "resolution": 78,
        "blank": 36,
        "duplicate": 50,
        "evaluable": 4480,
    }
    assert qc["received"] - sum(qc[k] for k in ("technical", "format", "resolution", "blank", "duplicate")) == qc["evaluable"]

    return {
        "primary": primary,
        "frames": frames,
        "stats": stats,
        "thresholds": thresholds,
        "calibration": calibration,
        "comparisons": comparisons,
        "friedman": friedman,
        "cv": cv,
        "subgroups": subgroups,
        "curves": {"grid": grid, "models": curves, "treat_all": treat_all},
        "cohort": {
            "D": cohort_row("Sitio D, desarrollo", dev),
            "train": cohort_row("Entrenamiento", parts["train"]),
            "val": cohort_row("Validación", parts["val"]),
            "test": cohort_row("Prueba interna", parts["test"]),
            "E1": cohort_row("Sitio E1, externo", e1),
            "E2": cohort_row("Sitio E2, externo", e2),
            "ext": cohort_row("Externa agrupada", pd.concat([e1, e2], ignore_index=True)),
        },
        "review": {
            "n": int(len(ext)),
            "agree1": agree1,
            "agree2": agree2,
            "kappa": kappa,
            "fn": int(fn.sum()),
            "fp": int(fp.sum()),
            "fn_rescued": fn_rescued,
            "fp_corrected": fp_corrected,
            "both_wrong_fn": both_wrong_fn,
            "n_time": n_time,
            "med_with": med_w,
            "q1_with": q1_w,
            "q3_with": q3_w,
            "med_without": med_o,
            "q1_without": q1_o,
            "q3_without": q3_o,
            "time_p": time_p,
        },
        "qc": qc,
        "versions": versions,
        "val_auc": val_auc,
    }


def _comma(x, _pos=None):
    return f"{x:.2f}".replace(".", ",")


def figures(R: dict) -> dict[str, Path]:
    FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.edgecolor": "#222222",
            "axes.labelcolor": "#222222",
            "xtick.color": "#222222",
            "ytick.color": "#222222",
            "text.color": "#222222",
            "axes.linewidth": 0.6,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    paths = {}
    paths["fig1"] = _fig_architecture(FIG / "fig1_arquitectura.png")
    paths["fig2"] = _fig_flow(R, FIG / "fig2_flujo.png")
    paths["fig3"] = _fig_roc(R, FIG / "fig3_roc.png")
    paths["fig4"] = _fig_calibration(R, FIG / "fig4_calibracion.png")
    paths["fig5"] = _fig_forest(R, FIG / "fig5_subgrupos.png")
    paths["fig6"] = _fig_decision(R, FIG / "fig6_decision.png")
    return paths


def _box(ax, x, y, w, h, text, fc):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.15,rounding_size=0.6",
            facecolor=fc,
            edgecolor="#243040",
            linewidth=0.7,
            mutation_aspect=0.6,
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.1, color="#14202b", linespacing=1.25)


def _arrow(ax, x1, y1, x2, y2):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color="#243040", lw=0.7),
    )


def _fig_architecture(path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11.4, 6.7), dpi=160)
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 78)
    ax.axis("off")
    roles = [
        (4, "Operador\ncasos, carga\ne inferencia"),
        (34, "Revisor\netiqueta final"),
        (64, "Auditor\nbitácora"),
        (94, "Administrador\nusuarios y\nreportes"),
    ]
    for x, text in roles:
        _box(ax, x, 64, 22, 11, text, "#d6e6f5")
        _arrow(ax, x + 11, 64, x + 11, 59)
    _box(ax, 18, 48, 84, 10, "Aplicación web  ·  React 18, TypeScript, Vite\nCasos, detalle, tablero y auditoría  ·  el rol recorta módulos y acciones", "#d9f0e4")
    _arrow(ax, 60, 48, 60, 43)
    _box(
        ax,
        14,
        30,
        92,
        12,
        "API clínica  ·  FastAPI, JWT, cuatro roles y cuenta de servicio\n"
        "Estados: creado → imagen cargada → completado, no evaluable o fallo técnico\n"
        "La regla de negocio y el permiso viven aquí; n8n solo orquesta",
        "#fff4d6",
    )
    _box(ax, 4, 12, 26, 14, "PostgreSQL\ncasos, inferencias,\nrevisiones\nauditoría inmutable\n(disparadores)", "#fde2c8")
    _box(ax, 33, 12, 26, 14, "Almacén de archivos\nimagen y mapa\nSHA-256\ninterfaz sustituible", "#fde2c8")
    _box(
        ax,
        62,
        10,
        54,
        16,
        "Motor intercambiable\n"
        "DenseNet121 · EfficientNet-B3 · ViT compacto\n"
        "CNN-Transformer · EfficientNet-BiLSTM-atención\n"
        "Umbral y Platt solo con validación  ·  Grad-CAM o atención",
        "#f6d6ea",
    )
    _arrow(ax, 28, 30, 17, 26)
    _arrow(ax, 48, 30, 46, 26)
    _arrow(ax, 78, 30, 86, 26)
    _box(
        ax,
        4,
        0.6,
        54,
        8.2,
        "n8n  ·  WF-01 importar  ·  WF-02 calidad  ·  WF-03 inferir\nWF-04 alertas sin identificadores  ·  WF-05 reporte  ·  WF-06 deriva",
        "#e7e2f5",
    )
    _box(
        ax,
        62,
        0.6,
        54,
        8.2,
        "Consultas  ·  solo agregados del tablero\nRAG por BM25 con rechazo si la evidencia no alcanza\nEl modelo de lenguaje no recibe imagen ni seudónimo",
        "#e7e2f5",
    )
    _arrow(ax, 30, 30, 30, 9.2)
    _arrow(ax, 90, 30, 90, 9.2)
    fig.tight_layout(pad=0.3)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _fig_flow(R: dict, path: Path) -> Path:
    q = R["qc"]
    c = R["cohort"]
    fig, ax = plt.subplots(figsize=(8.4, 9.4), dpi=160)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 118)
    ax.axis("off")

    def node(x, y, w, h, text, fc):
        _box(ax, x, y, w, h, text, fc)

    node(22, 106, 56, 8, f"Radiografías recibidas\nn = {q['received']}", "#d6e6f5")
    _arrow(ax, 50, 106, 50, 100)
    node(
        14,
        86,
        72,
        13,
        "Exclusiones antes del modelo\n"
        f"fallo técnico {q['technical']}  ·  formato o archivo ilegible {q['format']}\n"
        f"lado menor de 256 px {q['resolution']}  ·  imagen uniforme {q['blank']}\n"
        f"duplicado SHA-256 {q['duplicate']}",
        "#f8d0d0",
    )
    _arrow(ax, 50, 86, 50, 80)
    node(18, 70, 64, 9, f"Evaluables, una imagen por persona\nn = {q['evaluable']}", "#d9f0e4")
    _arrow(ax, 38, 70, 28, 62)
    _arrow(ax, 62, 70, 74, 62)
    node(
        6,
        46,
        40,
        15,
        "Sitio D, desarrollo\n"
        f"n = {c['D']['n']}\n"
        f"entrenamiento {c['train']['n']}\n"
        f"validación {c['val']['n']}  ·  prueba {c['test']['n']}",
        "#fff4d6",
    )
    node(
        54,
        46,
        40,
        15,
        "Externos, fuera del ajuste\n"
        f"E1 n = {c['E1']['n']}\n"
        f"E2 n = {c['E2']['n']}\n"
        f"agrupada n = {c['ext']['n']}",
        "#f6d6ea",
    )
    node(
        14,
        28,
        72,
        12,
        "Validación del sitio D\numbral (sensibilidad ≥ 90 %) y escalado de Platt\nno se reabren con la prueba interna ni con E1 o E2",
        "#e7e2f5",
    )
    _arrow(ax, 26, 46, 40, 40)
    node(
        14,
        8,
        72,
        14,
        "Desenlaces en imágenes evaluables\n"
        "tuberculosis probable  ·  sin hallazgos compatibles\n"
        "El estado no evaluable queda fuera del AUC\n"
        "La revisión humana puede cambiar la etiqueta final",
        "#d6e6f5",
    )
    _arrow(ax, 50, 28, 50, 22)
    fig.tight_layout(pad=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _fig_roc(R: dict, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6.7, 6.3), dpi=170)
    ax.plot([0, 1], [0, 1], color="#888888", lw=0.7, ls="--")
    primary = R["primary"]
    for name in MODELS:
        df = R["frames"][name]["ext"]
        fpr, tpr, _ = roc_curve(df["y"], df["p"])
        auc = R["stats"][name]["ext"]["auc_roc"]
        ax.plot(fpr, tpr, color=COLORS[name], lw=1.7 if name == primary else 1.25, label=f"{DISPLAY[name]}  {auc:.3f}".replace(".", ","))
        if name == primary:
            thr = R["thresholds"][name]["t90"]
            pred = df["p"] >= thr
            y = df["y"].to_numpy()
            sens = ((pred) & (y == 1)).sum() / (y == 1).sum()
            fpr_op = ((pred) & (y == 0)).sum() / (y == 0).sum()
            ax.scatter([fpr_op], [sens], s=36, color=COLORS[name], zorder=5, label="Umbral fijado en validación")
    ax.set_xlabel("Tasa de falsos positivos (1 − especificidad)")
    ax.set_ylabel("Sensibilidad")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_comma))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_comma))
    ax.legend(frameon=False, fontsize=7.4, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _reliability(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    xs, ys, ns = [], [], []
    for b in range(bins):
        m = idx == b
        if m.sum() >= 8:
            xs.append(p[m].mean())
            ys.append(y[m].mean())
            ns.append(int(m.sum()))
    return np.asarray(xs), np.asarray(ys), ns


def _fig_calibration(R: dict, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6.7, 6.2), dpi=170)
    ax.plot([0, 1], [0, 1], color="#888888", lw=0.7, ls="--", label="Calibración perfecta")
    primary = R["primary"]
    for name in MODELS:
        df = R["frames"][name]["ext"]
        xs, ys, _ = _reliability(df["y"].to_numpy(), df["p"].to_numpy())
        ece = R["stats"][name]["ext"]["ece"]
        ax.plot(
            xs,
            ys,
            marker="o",
            ms=3.5,
            lw=1.5 if name == primary else 1.05,
            color=COLORS[name],
            label=f"{DISPLAY[name]}  ECE {ece:.3f}".replace(".", ","),
        )
    raw = R["frames"][primary]["ext"]
    xs, ys, _ = _reliability(raw["y"].to_numpy(), raw["p_raw"].to_numpy())
    ax.plot(xs, ys, color=COLORS[primary], lw=1.1, ls=":", label="Seleccionado, antes de Platt")
    ax.set_xlabel("Probabilidad predicha")
    ax.set_ylabel("Frecuencia observada")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_comma))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_comma))
    ax.legend(frameon=False, fontsize=7.2, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _fig_forest(R: dict, path: Path) -> Path:
    rows = list(reversed(R["subgroups"]))
    fig, ax = plt.subplots(figsize=(7.6, 6.4), dpi=170)
    ys = np.arange(len(rows))
    overall = R["stats"][R["primary"]]["ext"]["auc_roc"]
    ax.axvline(overall, color="#888888", lw=0.7, ls="--")
    for i, row in enumerate(rows):
        ax.plot([row["lo"], row["hi"]], [i, i], color="#0072B2", lw=1.4)
        ax.plot(row["auc"], i, "o", color="#D55E00", ms=4.5)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r['label']}  (n = {r['n']})" for r in rows], fontsize=8)
    ax.set_xlabel("AUC-ROC (IC 95 % por remuestreo de pacientes)")
    ax.set_xlim(0.30, 0.98)
    ax.axvline(0.5, color="#bbbbbb", lw=0.5, ls=":")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_comma))
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _fig_decision(R: dict, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6.9, 5.7), dpi=170)
    grid = R["curves"]["grid"]
    primary = R["primary"]
    ax.plot(grid, R["curves"]["treat_all"], color="#888888", lw=1.0, label="Confirmar a todas las personas")
    ax.axhline(0, color="#444444", lw=0.6, label="No confirmar a nadie")
    ax.plot(grid, R["curves"]["models"]["densenet121"], color=COLORS["densenet121"], lw=1.4, label="DenseNet121")
    ax.plot(grid, R["curves"]["models"][primary], color=COLORS[primary], lw=1.8, label=DISPLAY[primary])
    thr = R["thresholds"][primary]["t90"]
    if 0.02 <= thr <= 0.60:
        ax.axvline(thr, color=COLORS[primary], lw=0.7, ls=":")
    ax.set_xlabel("Probabilidad umbral")
    ax.set_ylabel("Beneficio neto")
    ax.set_xlim(0.02, 0.60)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_comma))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_comma))
    ax.legend(frameon=False, fontsize=7.4, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


if __name__ == "__main__":
    import pickle

    R = build()
    figures(R)
    # Los marcos se conservan para las figuras ya escritas y para el manuscrito.
    out = OUT / "escenario.pkl"
    with out.open("wb") as fh:
        pickle.dump(R, fh)
    p = R["primary"]
    ext = R["stats"][p]["ext"]
    print("primary", p, "val", round(R["val_auc"][p], 3), "extAUC", round(ext["auc_roc"], 3))
    print("sens", round(ext["sensitivity"], 3), "spec", round(ext["specificity"], 3), "tpp", ext["tpp"])
    print("thr", round(R["thresholds"][p]["t90"], 3))
    for c in R["comparisons"]:
        print(c["name"], "dAUC", round(c["delong"]["auc_a"] - c["delong"]["auc_b"], 3), "p", round(c["delong"]["p"], 4), "holm", round(c["delong_holm"], 4))
    print("friedman", R["friedman"]["friedman_p"])
    print("kappa", round(R["review"]["kappa"], 3), "agree", round(R["review"]["agree1"], 3))
    print("saved", out)
