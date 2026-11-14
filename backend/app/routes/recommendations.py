from datetime import datetime, timezone

from flask import Blueprint, g, jsonify

from app.extensions import get_db
from app.models.user import iso
from app.routes.projects import public_project
from app.routes.requirements import _owned_project
from app.services.recommender import build_recommendation
from app.utils.auth import token_required

recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.get("/api/projects/<project_id>/recommendation")
@token_required
def get_recommendation(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404
    doc = get_db().recommendations.find_one({"project_id": project["_id"]})
    return jsonify(
        project=public_project(project),
        recommendation=doc["result"] if doc else None,
        created_at=iso(doc["created_at"]) if doc else None,
    ), 200


@recommendations_bp.post("/api/projects/<project_id>/recommend")
@token_required
def create_recommendation(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404

    db = get_db()
    req = db.requirements.find_one({"project_id": project["_id"]})
    if not req:
        return jsonify(error="Save the project requirements first."), 400

    try:
        result = build_recommendation(project["category"], req)
    except FileNotFoundError:
        return jsonify(error="ML models not found. Run ml/train_models.py first."), 500
    if not result["options"]:
        return jsonify(error="These requirements are too large for the instance catalog. Lower the CPU or RAM."), 422

    now = datetime.now(timezone.utc)
    db.recommendations.update_one(
        {"project_id": project["_id"]},
        {"$set": {"user_id": g.user["_id"], "result": result, "created_at": now}},
        upsert=True,
    )
    db.cost_estimates.update_one(
        {"project_id": project["_id"]},
        {
            "$set": {
                "user_id": g.user["_id"],
                "region": result["region"],
                "budget_usd_month": result["budget_usd"],
                "price_source": result["price_source"],
                "options": [
                    {"key": o["key"], "label": o["label"], "monthly_usd": o["monthly_usd"], "components": o["components"]}
                    for o in result["options"]
                ],
                "created_at": now,
            }
        },
        upsert=True,
    )
    db.projects.update_one({"_id": project["_id"]}, {"$set": {"status": "recommended"}})
    return jsonify(recommendation=result, created_at=iso(now)), 200
