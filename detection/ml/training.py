"""Compare calibrated candidates on validation data; evaluate once on test data."""
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from .preprocessing import build_preprocessor, feature_frame
from .schema import FEATURES, SCHEMA_VERSION


def evaluate(y_true, probability, threshold):
    prediction = probability >= threshold
    return {"accuracy": float(accuracy_score(y_true, prediction)),
            "precision": float(precision_score(y_true, prediction, zero_division=0)),
            "recall": float(recall_score(y_true, prediction, zero_division=0)),
            "f1": float(f1_score(y_true, prediction, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_true, probability)),
            "average_precision": float(average_precision_score(y_true, probability)),
            "brier_score": float(brier_score_loss(y_true, probability)),
            "confusion_matrix": confusion_matrix(y_true, prediction, labels=[0, 1]).tolist()}


def train(dataset_path, model_path, report_path, seed=42):
    dataset_path, model_path, report_path = map(Path, [dataset_path, model_path, report_path])
    raw = pd.read_csv(dataset_path)
    if "is_fraud" not in raw or not raw["is_fraud"].isin([0, 1]).all() or raw["is_fraud"].value_counts().min() < 20 or raw["is_fraud"].nunique() != 2:
        raise ValueError("Dataset needs binary is_fraud labels and at least 20 examples of each class.")
    X, y = feature_frame(raw), raw["is_fraud"].astype(int)
    X_development, X_test, y_development, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=seed)
    X_train, X_validation, y_train, y_validation = train_test_split(X_development, y_development, test_size=0.25, stratify=y_development, random_state=seed)
    classifiers = {
        "Logistic Regression": LogisticRegression(class_weight="balanced", max_iter=2000, random_state=seed),
        "Random Forest": RandomForestClassifier(n_estimators=160, max_depth=12, min_samples_leaf=3, class_weight="balanced_subsample", n_jobs=1, random_state=seed),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=120, learning_rate=0.05, max_depth=3, random_state=seed),
    }
    candidates, reports = {}, []
    for name, classifier in classifiers.items():
        pipeline = Pipeline([("preprocess", build_preprocessor()), ("classifier", classifier)])
        estimator = CalibratedClassifierCV(pipeline, method="sigmoid", cv=3)
        estimator.fit(X_train, y_train)
        probability = estimator.predict_proba(X_validation)[:, 1]
        thresholds = np.linspace(0.05, 0.80, 76)
        threshold = max(thresholds, key=lambda t: (f1_score(y_validation, probability >= t, zero_division=0), recall_score(y_validation, probability >= t, zero_division=0), -t))
        metrics = evaluate(y_validation, probability, threshold)
        reports.append({"name": name, "threshold": float(threshold), "validation": metrics})
        candidates[name] = estimator
    winner = max(reports, key=lambda r: (r["validation"]["f1"], r["validation"]["recall"], r["validation"]["roc_auc"]))
    final_model = clone(candidates[winner["name"]]).fit(X_development, y_development)
    test_metrics = evaluate(y_test, final_model.predict_proba(X_test)[:, 1], winner["threshold"])
    digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    version = f"v{SCHEMA_VERSION}-{digest[:10]}-{seed}"
    report = {"model_name": winner["name"], "model_version": version, "threshold": winner["threshold"],
              "trained_at": datetime.now(timezone.utc).isoformat(), "rows": len(raw), "fraud_count": int(y.sum()),
              "fraud_rate": float(y.mean()), "seed": seed, "dataset_sha256": digest,
              "split": {"train": len(X_train), "validation": len(X_validation), "test": len(X_test)},
              "selection_metric": "Validation F1, then recall, then ROC-AUC; validation-only threshold tuning",
              "candidates": reports, "test": test_metrics,
              "versions": {"python": platform.python_version(), "scikit_learn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__, "joblib": joblib.__version__}}
    artifact = {"schema_version": SCHEMA_VERSION, "features": FEATURES, "pipeline": final_model,
                "threshold": winner["threshold"], "model_version": version, "metadata": report}
    model_path.parent.mkdir(parents=True, exist_ok=True)
    # A temporary sibling prevents readers from opening a half-written artifact.
    temporary = model_path.with_suffix(".tmp")
    try:
        joblib.dump(artifact, temporary, compress=3)
        temporary.replace(model_path)
    finally:
        temporary.unlink(missing_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
