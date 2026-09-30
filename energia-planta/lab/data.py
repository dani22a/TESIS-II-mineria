"""Data loading, timestamp reconstruction, quality report and temporal split."""
from __future__ import annotations

import pandas as pd

from .config import DATA_PATH, DAYS, EXAM_START, INTERVAL_MIN

DATE_FORMAT = "%d/%m/%Y %H:%M"

# (low, high) validity rules; None means unbounded.
RANGE_RULES = {
    "Usage_kWh": (0, None),
    "Lagging_Current_Reactive.Power_kVarh": (0, None),
    "Leading_Current_Reactive_Power_kVarh": (0, None),
    "CO2(tCO2)": (0, None),
    "Lagging_Current_Power_Factor": (0, 100),
    "Leading_Current_Power_Factor": (0, 100),
    "NSM": (0, 86400),
}


def load_raw(path=DATA_PATH) -> pd.DataFrame:
    """Read the CSV as-is (BOM tolerant)."""
    return pd.read_csv(path, encoding="utf-8-sig")


def prepare(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse dates and rebuild timestamps consciously.

    The file stamps each record with the END of the 15-min interval, but the
    midnight record (NSM == 0) carries the date of the day it closes instead of
    the next day. We rebuild ``ts_end = day + NSM`` (+1 day when NSM == 0) and
    derive ``ts_start = ts_end - 15 min``; all time features and the temporal
    split use ``ts_start``.
    """
    df = raw.copy()
    df["date_label"] = pd.to_datetime(df["date"], format=DATE_FORMAT)
    ts_end = df["date_label"].dt.normalize() + pd.to_timedelta(df["NSM"], unit="s")
    ts_end = ts_end + pd.to_timedelta((df["NSM"] == 0).astype(int), unit="D")
    df["ts_end"] = ts_end
    df["ts_start"] = ts_end - pd.Timedelta(minutes=INTERVAL_MIN)
    df["hour_frac"] = df["ts_start"].dt.hour + df["ts_start"].dt.minute / 60.0
    df["hour"] = df["ts_start"].dt.hour
    df["day"] = df["ts_start"].dt.day_name()
    df["month"] = df["ts_start"].dt.month
    df = df.sort_values("ts_end").reset_index(drop=True)
    return df


def split_masks(df: pd.DataFrame):
    """Boolean masks (train, exam) by interval start: exam = Oct 1 onwards."""
    exam = df["ts_start"] >= EXAM_START
    return ~exam, exam


def quality_report(raw: pd.DataFrame, df: pd.DataFrame) -> dict:
    """Compute the data-quality report shown in the Datos screen."""
    expected = pd.date_range(df["ts_end"].min(), df["ts_end"].max(), freq=f"{INTERVAL_MIN}min")
    missing = expected.difference(pd.DatetimeIndex(df["ts_end"]))
    gaps = df["ts_end"].diff().dropna().value_counts().rename_axis("gap").reset_index(name="records")
    gaps["gap"] = gaps["gap"].astype(str)

    raw_label = pd.to_datetime(raw["date"], format=DATE_FORMAT)
    out_of_order = int((raw_label.diff().dropna() < pd.Timedelta(0)).sum())

    ranges = []
    for col, (lo, hi) in RANGE_RULES.items():
        s = raw[col]
        bad = 0
        if lo is not None:
            bad += int((s < lo).sum())
        if hi is not None:
            bad += int((s > hi).sum())
        ranges.append({
            "variable": col,
            "mín": float(s.min()),
            "máx": float(s.max()),
            "media": float(s.mean()),
            "ceros": int((s == 0).sum()),
            "nulos": int(s.isna().sum()),
            "regla": f"{'-inf' if lo is None else lo} a {'+inf' if hi is None else hi}",
            "fuera de rango": bad,
        })

    per_month = df.groupby(df["ts_end"].dt.to_period("M")).size()
    exp_month = pd.Series(expected.to_period("M")).value_counts()
    monthly = pd.DataFrame({
        "mes": per_month.index.astype(str),
        "registros": per_month.values,
        "esperados": [int(exp_month.get(p, 0)) for p in per_month.index],
    })

    checks = {
        "day_matches_label": int((df["day"] == df["Day_of_week"]).sum()),
        "weekstatus_consistent": int(
            (df["WeekStatus"] == df["day"].map(lambda d: "Weekend" if d in ("Saturday", "Sunday") else "Weekday")).sum()
        ),
        "nsm_multiple_of_900": int((df["NSM"] % 900 == 0).sum()),
        "unknown_days": int((~df["Day_of_week"].isin(DAYS)).sum()),
    }
    dtypes = pd.DataFrame({"columna": raw.columns, "tipo": [str(t) for t in raw.dtypes]})

    return {
        "n_rows": len(raw),
        "n_cols": raw.shape[1],
        "ts_end_min": df["ts_end"].min(),
        "ts_end_max": df["ts_end"].max(),
        "n_expected": len(expected),
        "n_missing": len(missing),
        "missing_head": [str(m) for m in missing[:10]],
        "raw_duplicate_labels": int(raw["date"].duplicated().sum()),
        "ts_duplicates": int(df["ts_end"].duplicated().sum()),
        "full_row_duplicates": int(raw.duplicated().sum()),
        "parse_failures": int(df["date_label"].isna().sum()),
        "midnight_records": int((raw["NSM"] == 0).sum()),
        "raw_out_of_order": out_of_order,
        "gaps": gaps,
        "ranges": pd.DataFrame(ranges),
        "monthly": monthly,
        "checks": checks,
        "dtypes": dtypes,
        "nulls_total": int(raw.isna().sum().sum()),
        "zero_kwh": int((raw["Usage_kWh"] == 0).sum()),
    }
