"""Statistical tests on the raw data (Pruebas phase). Model-comparison tests live in evaluation.py."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import scikit_posthocs as sp
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools import add_constant
from statsmodels.tsa.stattools import acf, kpss

from .config import LOAD_TYPES, TARGET
from .theme import COLUMN_SHORT

REACTIVE_PF = [
    "Lagging_Current_Reactive.Power_kVarh",
    "Leading_Current_Reactive_Power_kVarh",
    "Lagging_Current_Power_Factor",
    "Leading_Current_Power_Factor",
]
NUMERIC = REACTIVE_PF + ["CO2(tCO2)", "NSM"]


def kruskal_load(df: pd.DataFrame) -> dict:
    """Kruskal-Wallis on consumption by load type, with Dunn (Bonferroni) post hoc."""
    groups = [df.loc[df["Load_Type"] == t, TARGET].to_numpy() for t in LOAD_TYPES]
    h, p = stats.kruskal(*groups)
    n, k = len(df), len(groups)
    dunn = sp.posthoc_dunn(df, val_col=TARGET, group_col="Load_Type", p_adjust="bonferroni")
    dunn = dunn.loc[LOAD_TYPES, LOAD_TYPES]
    medians = df.groupby("Load_Type")[TARGET].median().reindex(LOAD_TYPES)
    return {"H": float(h), "p": float(p), "eps2": float((h - k + 1) / (n - k)), "dunn": dunn, "medians": medians}


def kruskal_hour(df: pd.DataFrame) -> dict:
    """Kruskal-Wallis on consumption by hour of day (24 groups)."""
    groups = [g[TARGET].to_numpy() for _, g in df.groupby("hour")]
    h, p = stats.kruskal(*groups)
    n, k = len(df), len(groups)
    prof = df.groupby("hour")[TARGET].mean()
    return {"H": float(h), "p": float(p), "eps2": float((h - k + 1) / (n - k)),
            "max_hour": int(prof.idxmax()), "min_hour": int(prof.idxmin()),
            "max": float(prof.max()), "min": float(prof.min())}


def mann_whitney_week(df: pd.DataFrame) -> dict:
    """Mann-Whitney: weekday vs weekend consumption."""
    is_weekend = df["day"].isin(["Saturday", "Sunday"])
    a = df.loc[~is_weekend, TARGET].to_numpy()
    b = df.loc[is_weekend, TARGET].to_numpy()
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return {
        "U": float(u), "p": float(p),
        "rank_biserial": float(2 * u / (len(a) * len(b)) - 1),
        "median_weekday": float(np.median(a)), "median_weekend": float(np.median(b)),
        "mean_weekday": float(a.mean()), "mean_weekend": float(b.mean()),
        "n_weekday": len(a), "n_weekend": len(b),
    }


def spearman_table(df: pd.DataFrame) -> pd.DataFrame:
    """Spearman correlation of each numeric variable with consumption."""
    rows = []
    for col in NUMERIC + ["hour_frac"]:
        rho, p = stats.spearmanr(df[col], df[TARGET])
        rows.append({"variable": col, "rho": float(rho), "p": float(p)})
    return pd.DataFrame(rows)


def spearman_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return df[[TARGET] + NUMERIC].corr(method="spearman")


def vif_table(df: pd.DataFrame) -> pd.DataFrame:
    """VIF with and without CO2 among consumption and the numeric signals."""
    def _vif(cols):
        x = add_constant(df[cols].astype(float))
        return {c: float(variance_inflation_factor(x.to_numpy(), i)) for i, c in enumerate(x.columns) if c != "const"}

    base = [TARGET, "CO2(tCO2)"] + REACTIVE_PF
    with_co2 = _vif(base)
    without = _vif([c for c in base if c != "CO2(tCO2)"])
    return pd.DataFrame({
        "variable": base,
        "VIF con CO2": [with_co2[c] for c in base],
        "VIF sin CO2": [without.get(c, np.nan) for c in base],
    })


def kpss_table(df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """KPSS (level and trend) on the 15-min series, plus lag-1 autocorrelation."""
    y = df.sort_values("ts_start")[TARGET].to_numpy()
    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for reg, label in (("c", "estacionaria en nivel"), ("ct", "estacionaria en tendencia")):
            stat, p, lags, _ = kpss(y, regression=reg, nlags="auto")
            rows.append({"hipótesis nula": label, "estadístico": float(stat), "p (acotado a 0.01-0.10)": float(p), "rezagos": int(lags)})
    ac = acf(y, nlags=96, fft=True)
    return pd.DataFrame(rows), {"lag1": float(ac[1]), "lag96": float(ac[96])}


def run_data_tests(df: pd.DataFrame) -> dict:
    kpss_df, ac = kpss_table(df)
    return {
        "kruskal_load": kruskal_load(df),
        "kruskal_hour": kruskal_hour(df),
        "mann_whitney": mann_whitney_week(df),
        "spearman": spearman_table(df),
        "spearman_matrix": spearman_matrix(df),
        "vif": vif_table(df),
        "kpss": kpss_df,
        "acf": ac,
    }


def _fmt_p(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def _diff_verdict(p: float, noun: str = "diferencia") -> str:
    return f"✅ {noun.capitalize()} significativa" if p < 0.05 else f"⚠️ Sin {noun} significativa"


def test_table(t: dict) -> pd.DataFrame:
    """Compact table: test, statistic, p and a one-line reading."""
    kl, kh, mw = t["kruskal_load"], t["kruskal_hour"], t["mann_whitney"]
    sp_ = t["spearman"].set_index("variable")
    vif = t["vif"].set_index("variable")
    rows = [
        {"prueba": "Kruskal-Wallis: consumo por tipo de carga", "estadístico": f"H = {kl['H']:,.0f}", "p": _fmt_p(kl["p"]), "veredicto": _diff_verdict(kl["p"]),
         "lectura": f"Las tres cargas tienen distribuciones distintas (tamaño de efecto {kl['eps2']:.2f})."},
        {"prueba": "Kruskal-Wallis: consumo por hora del día", "estadístico": f"H = {kh['H']:,.0f}", "p": _fmt_p(kh["p"]), "veredicto": _diff_verdict(kh["p"]),
         "lectura": f"El consumo cambia con la hora: de {kh['min']:.1f} kWh ({kh['min_hour']:02d}h) a {kh['max']:.1f} kWh ({kh['max_hour']:02d}h) en promedio."},
        {"prueba": "Mann-Whitney: día laborable vs fin de semana", "estadístico": f"U = {mw['U']:,.0f}", "p": _fmt_p(mw["p"]), "veredicto": _diff_verdict(mw["p"]),
         "lectura": f"Mediana {mw['median_weekday']:.1f} kWh entre semana y {mw['median_weekend']:.1f} kWh en fin de semana."},
    ]
    for col in NUMERIC:
        r = sp_.loc[col]
        rows.append({"prueba": f"Spearman: {COLUMN_SHORT[col].lower()} vs consumo", "estadístico": f"rho = {r['rho']:.2f}",
                     "p": _fmt_p(r["p"]), "veredicto": _diff_verdict(r["p"], "asociación"),
                     "lectura": "Asociación " + ("fuerte" if abs(r["rho"]) >= 0.7 else "moderada" if abs(r["rho"]) >= 0.4 else "débil") + "."})
    rows.append({"prueba": "VIF del CO2 (con el consumo en el conjunto)", "estadístico": f"VIF = {vif.loc['CO2(tCO2)', 'VIF con CO2']:.1f}", "p": "-",
                 "veredicto": "⚠️ Variable redundante" if vif.loc["CO2(tCO2)", "VIF con CO2"] > 10 else "✅ Sin redundancia",
                 "lectura": "Por encima de 10 indica redundancia: el CO2 es casi una copia del consumo."})
    k0 = t["kpss"].iloc[0]
    rows.append({"prueba": "KPSS sobre la serie de 15 min (estabilidad del nivel)", "estadístico": f"{k0['estadístico']:.2f}", "p": f"<= {k0['p (acotado a 0.01-0.10)']:.2f}"
                 if k0["p (acotado a 0.01-0.10)"] <= 0.01 else f"{k0['p (acotado a 0.01-0.10)']:.2f}",
                 "veredicto": "⚠️ Serie no estacionaria" if k0["p (acotado a 0.01-0.10)"] < 0.05 else "✅ Serie estacionaria",
                 "lectura": "Se rechaza la estacionariedad." if k0["p (acotado a 0.01-0.10)"] < 0.05 else "No se rechaza la estacionariedad."})
    return pd.DataFrame(rows)


def variable_decisions(t: dict) -> pd.DataFrame:
    """Decision table: which variables enter the model, justified by the tests."""
    kl, kh, mw = t["kruskal_load"], t["kruskal_hour"], t["mann_whitney"]
    sp_ = t["spearman"].set_index("variable")["rho"]
    vif = t["vif"].set_index("variable")
    rho_nsm_hour = None
    rows = [
        ("Hora del día (seno y coseno)", "✅ Entra al modelo",
         f"Kruskal-Wallis por hora H = {kh['H']:,.0f} (p {_fmt_p(kh['p'])}); perfil de {kh['min']:.1f} a {kh['max']:.1f} kWh."),
        ("Día de la semana", "✅ Entra al modelo",
         f"Mann-Whitney p {_fmt_p(mw['p'])}: mediana {mw['median_weekday']:.1f} kWh entre semana frente a {mw['median_weekend']:.1f} kWh en fin de semana."),
        ("Tipo de carga", "✅ Entra al modelo",
         f"Kruskal-Wallis H = {kl['H']:,.0f} (p {_fmt_p(kl['p'])}), efecto {kl['eps2']:.2f}; Dunn separa las tres cargas."),
        ("Potencia reactiva (inductiva / capacitiva)", "❌ No entra",
         f"rho = {sp_['Lagging_Current_Reactive.Power_kVarh']:.2f} / {sp_['Leading_Current_Reactive_Power_kVarh']:.2f}: informan, pero el gemelo no las produce."),
        ("Factor de potencia (inductivo / capacitivo)", "❌ No entra",
         f"rho = {sp_['Lagging_Current_Power_Factor']:.2f} / {sp_['Leading_Current_Power_Factor']:.2f}: solo para entender el archivo."),
        ("Segundos desde medianoche (NSM)", "❌ No entra",
         f"rho = {sp_['NSM']:.2f} con kWh; son los segundos desde medianoche, redundante con la hora."),
        ("CO2 (tCO2)", "❌ No entra",
         f"rho = {sp_['CO2(tCO2)']:.2f} y VIF = {vif.loc['CO2(tCO2)', 'VIF con CO2']:.0f}: copia del consumo; se calcula después desde kWh."),
        ("Tipo de día (WeekStatus)", "❌ No entra", "Se deriva del día de la semana."),
    ]
    return pd.DataFrame(rows, columns=["variable", "decisión", "evidencia"])
