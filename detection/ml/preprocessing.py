"""Shared, fitted-inside-the-split feature preparation."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from .schema import BOOLEAN_FEATURES, BOUNDS, CATEGORICAL_FEATURES, CHOICES, FEATURES, NUMERIC_FEATURES


def feature_frame(data):
    frame = pd.DataFrame(data).copy()
    if "transaction_datetime" not in frame:
        raise ValueError("Transaction date & time is required.")
    dates = pd.to_datetime(frame["transaction_datetime"], errors="raise", utc=True)
    if dates.isna().any():
        raise ValueError("Transaction dates cannot be empty.")
    frame["hour"] = dates.dt.hour
    missing = set(FEATURES) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing features: {', '.join(sorted(missing))}.")
    for name in NUMERIC_FEATURES + BOOLEAN_FEATURES:
        frame[name] = pd.to_numeric(frame[name], errors="raise")
        if not np.isfinite(frame[name].to_numpy(dtype=float)).all():
            raise ValueError(f"{name} must contain finite numbers.")
        low, high = BOUNDS.get(name, (0, 1))
        if not frame[name].between(low, high).all():
            raise ValueError(f"{name} must be between {low} and {high}.")
        if name in BOOLEAN_FEATURES + ["previous_transactions_count", "transaction_frequency"] and (frame[name] % 1 != 0).any():
            raise ValueError(f"{name} must contain whole numbers.")
    for name in CATEGORICAL_FEATURES:
        if not frame[name].isin([value for value, _ in CHOICES[name]]).all():
            raise ValueError(f"Unsupported {name} value.")
    if ((frame["online_order"] == 1) & (frame["transaction_type"] != "Online")).any():
        raise ValueError("An online order must use the Online transaction type.")
    return frame[FEATURES]


def build_preprocessor():
    return ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC_FEATURES),
        ("category", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ("security", "passthrough", BOOLEAN_FEATURES),
    ])
