import json
import os
from pathlib import Path

from flask import Blueprint, g, jsonify

from app.extensions import get_db
from app.services import aws_client, deployer
from app.utils.auth import token_required

settings_bp = Blueprint("settings", __name__)
METRICS = Path(__file__).resolve().parents[3] / "ml" / "models" / "metrics.json"


def _model_info():
    try:
        m = json.loads(METRICS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"available": False}
    rf = m.get("regression", {}).get("Random Forest", {})
    lr = m.get("regression", {}).get("Linear Regression", {})
    return {
        "available": True,
        "data_source": m.get("data_source"),
        "warning": m.get("warning"),
        "train_rows": m.get("train_rows"),
        "test_rows": m.get("test_rows"),
        "rf_r2_vcpu": rf.get("r2_vcpu"),
        "rf_r2_ram": rf.get("r2_ram"),
        "lr_r2_vcpu": lr.get("r2_vcpu"),
        "lr_r2_ram": lr.get("r2_ram"),
        "classifier": m.get("classification_model_saved"),
        "classifier_accuracy": m.get("classification", {}).get(m.get("classification_model_saved", ""), {}).get("accuracy"),
    }


@settings_bp.get("/api/settings")
@token_required
def settings():
    db = get_db()
    uid = g.user["_id"]
    return jsonify(
        aws=aws_client.status(),
        deploy_enabled=deployer.enabled(),
        cost_cap=deployer.cost_cap(),
        pricing_mode=os.getenv("PRICING_MODE", "reference").lower(),
        default_region=os.getenv("AWS_DEFAULT_REGION", "not set"),
        model=_model_info(),
        counts={
            "projects": db.projects.count_documents({"user_id": uid}),
            "recommendations": db.recommendations.count_documents({"user_id": uid}),
            "deployments": db.deployment_runs.count_documents({"user_id": uid}),
        },
    ), 200
