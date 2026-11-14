from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from app.extensions import get_db
from app.models.user import iso
from app.routes.requirements import _owned_project
from app.services.diagram import build_mermaid
from app.utils.auth import token_required

approval_bp = Blueprint("approval", __name__)


def _recommendation(project):
    doc = get_db().recommendations.find_one({"project_id": project["_id"]})
    return doc["result"] if doc else None


def public_approval(doc):
    if not doc:
        return None
    opt = doc["option"]
    return {
        "id": str(doc["_id"]),
        "status": doc["status"],
        "option_key": opt["key"],
        "option_label": opt["label"],
        "compute": opt["compute"],
        "monthly_usd": opt["monthly_usd"],
        "within_budget": opt["within_budget"],
        "region": doc["region"],
        "approved_at": iso(doc["approved_at"]),
    }


@approval_bp.get("/api/projects/<project_id>/architecture")
@token_required
def architecture(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404
    rec = _recommendation(project)
    if not rec:
        return jsonify(error="Generate the recommendation first."), 400
    diagrams = [
        {"key": o["key"], "label": o["label"], "mermaid": build_mermaid(rec, o)}
        for o in rec["options"]
    ]
    return jsonify(diagrams=diagrams), 200


@approval_bp.get("/api/projects/<project_id>/approval")
@token_required
def get_approval(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404
    doc = get_db().deployments.find_one(
        {"project_id": project["_id"]}, sort=[("approved_at", -1)]
    )
    return jsonify(approval=public_approval(doc)), 200


@approval_bp.post("/api/projects/<project_id>/approve")
@token_required
def approve(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404
    rec = _recommendation(project)
    if not rec:
        return jsonify(error="Generate the recommendation first."), 400

    data = request.get_json(silent=True) or {}
    if data.get("confirm") is not True:
        return jsonify(error="Tick the confirmation box to approve."), 400
    if str(data.get("confirm_name", "")).strip() != project["name"]:
        return jsonify(error="Type the exact project name to approve."), 400

    option = next((o for o in rec["options"] if o["key"] == data.get("option_key")), None)
    if not option:
        return jsonify(error="Choose one of the recommended options."), 400

    now = datetime.now(timezone.utc)
    db = get_db()
    db.deployments.update_one(
        {"project_id": project["_id"], "status": "approved"},
        {
            "$set": {
                "user_id": g.user["_id"],
                "region": rec["region"],
                "option": option,
                "approved_at": now,
            }
        },
        upsert=True,
    )
    db.projects.update_one({"_id": project["_id"]}, {"$set": {"status": "approved"}})
    doc = db.deployments.find_one({"project_id": project["_id"], "status": "approved"})
    return jsonify(approval=public_approval(doc)), 200
