from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError
from flask import Blueprint, jsonify, request

from app.extensions import get_db
from app.routes.requirements import _owned_project
from app.services.monitor import collect
from app.utils.auth import token_required

monitoring_bp = Blueprint("monitoring", __name__)


@monitoring_bp.get("/api/projects/<project_id>/monitoring")
@token_required
def monitoring(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404
    try:
        hours = int(request.args.get("hours", "3"))
    except ValueError:
        hours = 3
    if hours not in (1, 3, 6, 24):
        hours = 3

    db = get_db()
    run = db.deployment_runs.find_one({"project_id": project["_id"]}, sort=[("created_at", -1)])
    if not run or run["status"] != "deployed":
        return jsonify(available=False,
                       reason="Monitoring needs a deployed stack. Deploy this project first (Deploy tab)."), 200
    try:
        result = collect(run, hours)
    except (ClientError, BotoCoreError) as exc:
        if isinstance(exc, ClientError):
            err = exc.response["Error"]
            msg = err.get("Code", "Error") + ": " + err.get("Message", "")
        else:
            msg = "Could not reach AWS: " + type(exc).__name__
        return jsonify(error=msg), 502

    now = datetime.now(timezone.utc)
    db.monitoring.update_one(
        {"project_id": project["_id"]},
        {"$set": {"user_id": project["user_id"], "stack_name": run["stack_name"], "hours": hours,
                  "alarms": result["alarms"], "charts": result["charts"], "fetched_at": now}},
        upsert=True,
    )
    return jsonify(available=True, stack_name=run["stack_name"], region=run["region"], **result), 200
