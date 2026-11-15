from flask import Blueprint, jsonify, request

from app.extensions import get_db
from app.routes.requirements import _owned_project
from app.services.assistant import answer
from app.utils.auth import token_required

assistant_bp = Blueprint("assistant", __name__)


@assistant_bp.post("/api/assistant")
@token_required
def ask():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not 2 <= len(message) <= 500:
        return jsonify(error="Type a question of 2 to 500 characters."), 400

    rec, project = None, None
    project_id = str(data.get("project_id", "")).strip()
    if project_id:
        project = _owned_project(project_id)
        if not project:
            return jsonify(error="Project not found."), 404
        doc = get_db().recommendations.find_one({"project_id": project["_id"]})
        rec = doc["result"] if doc else None
    result = answer(message, rec, project)
    result["used_project"] = bool(rec)
    return jsonify(result), 200
