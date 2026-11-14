from flask import Blueprint, jsonify
from app.extensions import get_db

health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
def health():
    try:
        get_db().command("ping")
        return jsonify(status="ok", database="connected"), 200
    except Exception as exc:
        return jsonify(status="error", database="unreachable",
                       detail=type(exc).__name__), 503
