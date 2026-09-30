"""Feature engineering and the ONE shared preprocessing spec (used by lab, export and twin contract)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

from .config import DAYS, LOAD_TYPES

RAW_FEATURES = ["hour_sin", "hour_cos", "day", "load_type"]
CYCLIC = ["hour_sin", "hour_cos"]
CATEGORICAL = ["day", "load_type"]


def cyclic_hour(hour_frac) -> tuple[np.ndarray, np.ndarray]:
    """Encode the fractional hour of day (0-23.75) on a circle of period 24."""
    angle = 2 * np.pi * np.asarray(hour_frac, dtype=float) / 24.0
    return np.sin(angle), np.cos(angle)


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Model inputs from a prepared frame: hour_sin, hour_cos, day, load_type."""
    s, c = cyclic_hour(df["hour_frac"])
    return pd.DataFrame(
        {"hour_sin": s, "hour_cos": c, "day": df["day"].to_numpy(), "load_type": df["Load_Type"].to_numpy()},
        index=df.index,
    )


def scenario_features(hour_frac, day: str, load_type: str) -> pd.DataFrame:
    """Feature rows for scenario lookups (the twin's inputs) with the same encoding as training."""
    hour_frac = np.atleast_1d(np.asarray(hour_frac, dtype=float))
    s, c = cyclic_hour(hour_frac)
    return pd.DataFrame({"hour_sin": s, "hour_cos": c, "day": day, "load_type": load_type})


def build_preprocessor() -> ColumnTransformer:
    """Shared ColumnTransformer: hour sin/cos pass through, day and load type are one-hot encoded.

    Categories are fixed (never learned from data) so that train, exam and the twin see identical columns.
    """
    return ColumnTransformer(
        [
            ("cyclic", "passthrough", CYCLIC),
            ("categorical", OneHotEncoder(categories=[DAYS, LOAD_TYPES], sparse_output=False), CATEGORICAL),
        ],
        verbose_feature_names_out=False,
    )


def feature_names() -> list[str]:
    """Output column names of the preprocessor, in order."""
    return CYCLIC + [f"day_{d}" for d in DAYS] + [f"load_type_{t}" for t in LOAD_TYPES]
