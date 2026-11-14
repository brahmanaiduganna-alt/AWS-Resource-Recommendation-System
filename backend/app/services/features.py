import numpy as np
import pandas as pd

PERF_SCORE = {"low": 1, "medium": 2, "high": 3}

CATEGORICAL_FEATURES = ["category"]
NUMERIC_FEATURES = [
    "users_k",
    "log_users",
    "log_traffic",
    "log_storage",
    "traffic_per_user_mb",
    "perf_score",
]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def engineer(df):
    """Turn raw requirement columns into model features.

    Needs columns: category, users, traffic_gb_month, storage_gb, performance.
    """
    users = df["users"].astype(float)
    traffic = df["traffic_gb_month"].astype(float)
    storage = df["storage_gb"].astype(float)

    out = pd.DataFrame(index=df.index)
    out["category"] = df["category"].astype(str)
    out["users_k"] = users / 1000.0
    out["log_users"] = np.log1p(users)
    out["log_traffic"] = np.log1p(traffic)
    out["log_storage"] = np.log1p(storage)
    out["traffic_per_user_mb"] = traffic * 1024.0 / users.clip(lower=1)
    out["perf_score"] = df["performance"].map(PERF_SCORE).astype(float)
    return out[FEATURE_COLUMNS]
