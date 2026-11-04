"""Patient/institution-grouped splits with explicit leakage assertions."""
from __future__ import annotations

import itertools

import pandas as pd
from sklearn.model_selection import GroupKFold, GroupShuffleSplit


class LeakageError(AssertionError):
    pass


def assert_no_leakage(splits: dict[str, pd.DataFrame], group_col: str = "patient_id",
                      content_col: str | None = "sha256") -> None:
    """Splits must be pairwise disjoint on the group id (patient) and on image content hash."""
    for (na, a), (nb, b) in itertools.combinations(splits.items(), 2):
        if a.empty or b.empty:
            continue
        shared = set(a[group_col]) & set(b[group_col])
        if shared:
            raise LeakageError(f"{len(shared)} {group_col}(s) shared between {na} and {nb}")
        if content_col and content_col in a and content_col in b:
            shared = set(a[content_col]) & set(b[content_col])
            if shared:
                raise LeakageError(f"{len(shared)} identical image(s) shared between {na} and {nb}")


def _has_both(df: pd.DataFrame) -> bool:
    return df["label"].nunique() == 2


def split_manifest(df: pd.DataFrame, group_col: str = "patient_id", val_size: float = 0.2,
                   test_size: float = 0.2, seed: int = 0,
                   external_institutions: tuple[str, ...] = (), tries: int = 50) -> dict[str, pd.DataFrame]:
    """train/val/test by GroupShuffleSplit on `group_col`; rows from `external_institutions` form a
    separate external set that never touches development (threshold, calibration, tuning)."""
    df = df.reset_index(drop=True)
    external = df[df["institution"].isin(external_institutions)]
    dev = df[~df["institution"].isin(external_institutions)].reset_index(drop=True)
    for k in range(tries):
        s = seed + k
        tv_i, te_i = next(GroupShuffleSplit(1, test_size=test_size, random_state=s)
                          .split(dev, dev["label"], dev[group_col]))
        trval, test = dev.iloc[tv_i].reset_index(drop=True), dev.iloc[te_i].reset_index(drop=True)
        tr_i, va_i = next(GroupShuffleSplit(1, test_size=val_size / (1 - test_size), random_state=s)
                          .split(trval, trval["label"], trval[group_col]))
        train, val = trval.iloc[tr_i], trval.iloc[va_i]
        if all(_has_both(x) for x in (train, val, test)):
            splits = {"train": train.reset_index(drop=True), "val": val.reset_index(drop=True), "test": test}
            if len(external):
                splits["external"] = external.reset_index(drop=True)
                if set(external["institution"]) & set(dev["institution"]):
                    raise LeakageError("external institution also present in development data")
            assert_no_leakage(splits, group_col)
            return splits
    raise ValueError("could not build splits containing both classes in train/val/test")


def grouped_kfold(df: pd.DataFrame, n_splits: int = 5, group_col: str = "patient_id"):
    """Yield (fold, train_df, val_df). With group_col='institution' this is leave-institution-out."""
    df = df.reset_index(drop=True)
    for fold, (a, b) in enumerate(GroupKFold(n_splits=n_splits).split(df, df["label"], df[group_col])):
        tr, va = df.iloc[a], df.iloc[b]
        assert_no_leakage({"train": tr, "val": va}, group_col)
        yield fold, tr.reset_index(drop=True), va.reset_index(drop=True)
