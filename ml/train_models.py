import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    r2_score,
    silhouette_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from app.services.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, engineer  # noqa: E402

DATA_FILE = ROOT / "data" / "synthetic_dataset.csv"
MODELS_DIR = ROOT / "models"
SEED = 42


def make_pre():
    return ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("num", StandardScaler(), NUMERIC_FEATURES),
        ]
    )


def main():
    if not DATA_FILE.exists():
        raise SystemExit("Dataset missing. Run generate_dataset.py first.")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_FILE)
    X = engineer(df)
    y_reg = df[["need_vcpu", "need_ram_gb"]]
    y_cls = df["instance_family"]

    X_tr, X_te, yr_tr, yr_te, yc_tr, yc_te = train_test_split(
        X, y_reg, y_cls, test_size=0.2, random_state=SEED, stratify=y_cls
    )
    print(f"Train rows: {len(X_tr)}   Test rows: {len(X_te)}\n")

    # ---- Regression: how many vCPUs and how much RAM are needed ----
    regressors = {
        "Random Forest": Pipeline([("pre", make_pre()), ("model", RandomForestRegressor(n_estimators=200, random_state=SEED, n_jobs=-1))]),
        "Linear Regression": Pipeline([("pre", make_pre()), ("model", LinearRegression())]),
    }
    reg_metrics = {}
    for name, pipe in regressors.items():
        pipe.fit(X_tr, yr_tr)
        pred = pipe.predict(X_te)
        r2 = r2_score(yr_te, pred, multioutput="raw_values")
        mae = mean_absolute_error(yr_te, pred, multioutput="raw_values")
        reg_metrics[name] = {
            "r2_vcpu": float(r2[0]),
            "r2_ram": float(r2[1]),
            "mae_vcpu": float(mae[0]),
            "mae_ram_gb": float(mae[1]),
        }
    cv = cross_val_score(regressors["Random Forest"], X_tr, yr_tr, cv=5, scoring="r2")
    reg_metrics["Random Forest"]["cv_r2_mean"] = float(cv.mean())

    print("REGRESSION (test set)")
    print(f"{'Model':<20}{'R2 vCPU':>9}{'R2 RAM':>9}{'MAE vCPU':>10}{'MAE RAM GB':>12}")
    for name, m in reg_metrics.items():
        print(f"{name:<20}{m['r2_vcpu']:>9.3f}{m['r2_ram']:>9.3f}{m['mae_vcpu']:>10.2f}{m['mae_ram_gb']:>12.2f}")
    print(f"Random Forest 5-fold CV R2 (train set): {cv.mean():.3f}\n")

    # ---- Classification: which instance family ----
    classifiers = {
        "Decision Tree": Pipeline([("pre", make_pre()), ("model", DecisionTreeClassifier(max_depth=8, random_state=SEED))]),
        "Random Forest": Pipeline([("pre", make_pre()), ("model", RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1))]),
    }
    cls_metrics = {}
    for name, pipe in classifiers.items():
        pipe.fit(X_tr, yc_tr)
        pred = pipe.predict(X_te)
        cls_metrics[name] = {
            "accuracy": float(accuracy_score(yc_te, pred)),
            "f1_macro": float(f1_score(yc_te, pred, average="macro")),
        }
    best_cls = max(cls_metrics, key=lambda n: cls_metrics[n]["f1_macro"])

    print("CLASSIFICATION: instance family (test set)")
    print(f"{'Model':<20}{'Accuracy':>10}{'F1 macro':>10}")
    for name, m in cls_metrics.items():
        print(f"{name:<20}{m['accuracy']:>10.3f}{m['f1_macro']:>10.3f}")
    print(f"Saved as family model: {best_cls}\n")

    # ---- K-Means: group similar workloads ----
    cluster_pipe = Pipeline(
        [("scale", StandardScaler()), ("kmeans", KMeans(n_clusters=4, n_init=10, random_state=SEED))]
    )
    Xn = X[NUMERIC_FEATURES]
    cluster_pipe.fit(Xn)
    labels = cluster_pipe.predict(Xn)
    sil = float(silhouette_score(cluster_pipe[:-1].transform(Xn), labels, sample_size=2000, random_state=SEED))
    print(f"K-MEANS (4 workload groups)  silhouette score: {sil:.3f}")
    summary = (
        df.assign(cluster=labels)
        .groupby("cluster")[["users", "traffic_gb_month", "storage_gb"]]
        .median()
        .round(0)
    )
    summary["rows"] = pd.Series(labels).value_counts().sort_index()
    print(summary, "\n")

    # ---- Save ----
    joblib.dump(regressors["Random Forest"], MODELS_DIR / "resource_regressor.joblib")
    joblib.dump(classifiers[best_cls], MODELS_DIR / "family_classifier.joblib")
    joblib.dump(cluster_pipe, MODELS_DIR / "workload_clusters.joblib")

    report = {
        "data_source": "synthetic",
        "warning": "Trained on synthetic data. Scores show the model learned the generator rules, not real AWS behaviour.",
        "sklearn_version": sklearn.__version__,
        "train_rows": int(len(X_tr)),
        "test_rows": int(len(X_te)),
        "regression": reg_metrics,
        "regression_model_saved": "Random Forest",
        "classification": cls_metrics,
        "classification_model_saved": best_cls,
        "kmeans_silhouette": sil,
    }
    (MODELS_DIR / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Saved models and metrics.json to", MODELS_DIR)


if __name__ == "__main__":
    main()
