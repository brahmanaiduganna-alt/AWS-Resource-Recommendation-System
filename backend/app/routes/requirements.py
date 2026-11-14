import math
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, g, jsonify, request

from app.extensions import get_db
from app.models.user import iso
from app.routes.projects import public_project
from app.utils.auth import token_required
from app.utils.constants import CATEGORY_INFO, PERFORMANCE_LEVELS, REGIONS

requirements_bp = Blueprint("requirements", __name__)

# key: (label, minimum, maximum, whole number only)
FIELDS = {
    "users": ("Expected users", 1, 100_000_000, True),
    "cpu_vcpu": ("CPU (vCPUs)", 1, 128, True),
    "ram_gb": ("RAM (GB)", 1, 1024, True),
    "storage_gb": ("Storage (GB)", 1, 100_000, True),
    "traffic_gb_month": ("Monthly data transfer (GB)", 0, 1_000_000, False),
    "budget_usd_month": ("Monthly budget (USD)", 1, 1_000_000, False),
}


def _parse_number(data, key):
    label, low, high, whole = FIELDS[key]
    raw = data.get(key)
    if isinstance(raw, bool) or raw is None or str(raw).strip() == "":
        return None, f"{label} is required."
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None, f"{label} must be a number."
    if not math.isfinite(value):
        return None, f"{label} must be a number."
    if whole and not value.is_integer():
        return None, f"{label} must be a whole number."
    if not low <= value <= high:
        return None, f"{label} must be between {low:,} and {high:,}."
    return (int(value) if whole else round(value, 2)), None


def _owned_project(project_id):
    try:
        oid = ObjectId(project_id)
    except InvalidId:
        return None
    return get_db().projects.find_one({"_id": oid, "user_id": g.user["_id"]})


def public_requirements(doc):
    if not doc:
        return None
    out = {key: doc[key] for key in FIELDS}
    out["region"] = doc["region"]
    out["performance"] = doc["performance"]
    out["updated_at"] = iso(doc.get("updated_at"))
    return out


@requirements_bp.get("/api/meta")
def meta():
    return jsonify(
        categories=CATEGORY_INFO, regions=REGIONS, performance_levels=PERFORMANCE_LEVELS
    ), 200


@requirements_bp.get("/api/projects/<project_id>/requirements")
@token_required
def get_requirements(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404
    doc = get_db().requirements.find_one({"project_id": project["_id"]})
    return jsonify(project=public_project(project), requirements=public_requirements(doc)), 200


@requirements_bp.put("/api/projects/<project_id>/requirements")
@token_required
def save_requirements(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404

    data = request.get_json(silent=True) or {}
    values = {}
    for key in FIELDS:
        value, problem = _parse_number(data, key)
        if problem:
            return jsonify(error=problem), 400
        values[key] = value

    region = str(data.get("region", "")).strip()
    if region not in {r["code"] for r in REGIONS}:
        return jsonify(error="Choose a valid AWS region."), 400
    performance = str(data.get("performance", "")).strip().lower()
    if performance not in PERFORMANCE_LEVELS:
        return jsonify(error="Choose a valid performance level."), 400

    now = datetime.now(timezone.utc)
    db = get_db()
    db.requirements.update_one(
        {"project_id": project["_id"]},
        {
            "$set": {
                **values,
                "region": region,
                "performance": performance,
                "user_id": g.user["_id"],
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    db.projects.update_one(
        {"_id": project["_id"], "status": "draft"},
        {"$set": {"status": "requirements_saved"}},
    )
    doc = db.requirements.find_one({"project_id": project["_id"]})
    return jsonify(requirements=public_requirements(doc)), 200
