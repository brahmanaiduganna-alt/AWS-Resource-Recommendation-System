from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, g, jsonify, request

from app.extensions import get_db
from app.models.user import iso
from app.utils.auth import token_required
from app.utils.constants import CATEGORIES

projects_bp = Blueprint("projects", __name__)


def public_project(p):
    return {
        "id": str(p["_id"]),
        "name": p["name"],
        "category": p["category"],
        "description": p.get("description", ""),
        "status": p.get("status", "draft"),
        "created_at": iso(p.get("created_at")),
    }


@projects_bp.get("/api/projects/categories")
def categories():
    return jsonify(categories=CATEGORIES), 200


@projects_bp.get("/api/projects")
@token_required
def list_projects():
    cursor = (
        get_db()
        .projects.find({"user_id": g.user["_id"]})
        .sort("created_at", -1)
        .limit(100)
    )
    return jsonify(projects=[public_project(p) for p in cursor]), 200


@projects_bp.post("/api/projects")
@token_required
def create_project():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    category = str(data.get("category", "")).strip()
    description = str(data.get("description", "")).strip()

    if not 3 <= len(name) <= 80:
        return jsonify(error="Project name must be 3 to 80 characters."), 400
    if category not in CATEGORIES:
        return jsonify(error="Choose a valid project category."), 400
    if len(description) > 500:
        return jsonify(error="Description must be at most 500 characters."), 400

    project = {
        "user_id": g.user["_id"],
        "name": name,
        "category": category,
        "description": description,
        "status": "draft",
        "created_at": datetime.now(timezone.utc),
    }
    result = get_db().projects.insert_one(project)
    project["_id"] = result.inserted_id
    return jsonify(project=public_project(project)), 201


@projects_bp.delete("/api/projects/<project_id>")
@token_required
def delete_project(project_id):
    try:
        oid = ObjectId(project_id)
    except InvalidId:
        return jsonify(error="Invalid project id."), 400
    result = get_db().projects.delete_one({"_id": oid, "user_id": g.user["_id"]})
    if result.deleted_count == 0:
        return jsonify(error="Project not found."), 404
    get_db().requirements.delete_many({"project_id": oid})
    return jsonify(message="Project deleted."), 200
