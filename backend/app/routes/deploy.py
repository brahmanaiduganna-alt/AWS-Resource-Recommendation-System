from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError
from flask import Blueprint, g, jsonify, request

from app.extensions import get_db
from app.models.user import iso
from app.routes.approval import public_approval
from app.routes.requirements import _owned_project
from app.services import aws_client, deployer
from app.services.cfn_template import build_template, check_template
from app.utils.auth import token_required

deploy_bp = Blueprint("deploy", __name__)
PROJECT_STATUS = {"deployed": "deployed", "failed": "deploy_failed", "deleted": "approved"}


def public_run(r):
    return {
        "id": str(r["_id"]),
        "project_id": str(r["project_id"]),
        "project_name": r["project_name"],
        "stack_name": r["stack_name"],
        "region": r["region"],
        "option_label": r["option_label"],
        "compute": r["compute"],
        "monthly_usd": r["monthly_usd"],
        "status": r["status"],
        "aws_status": r.get("aws_status", ""),
        "reason": r.get("reason", ""),
        "outputs": r.get("outputs", []),
        "created_at": iso(r.get("created_at")),
        "updated_at": iso(r.get("updated_at")),
    }


def _refresh(run):
    if run["status"] not in ("creating", "deleting"):
        return run
    try:
        info = deployer.describe(run["stack_id"], run["region"])
    except (ClientError, BotoCoreError):
        return run
    status = deployer.map_status(info["aws_status"])
    changes = {
        "status": status,
        "aws_status": info["aws_status"],
        "reason": info["reason"],
        "outputs": info["outputs"],
        "updated_at": datetime.now(timezone.utc),
    }
    db = get_db()
    db.deployment_runs.update_one({"_id": run["_id"]}, {"$set": changes})
    if status in PROJECT_STATUS:
        db.projects.update_one({"_id": run["project_id"]}, {"$set": {"status": PROJECT_STATUS[status]}})
    run.update(changes)
    return run


def _latest_run(project_oid):
    return get_db().deployment_runs.find_one({"project_id": project_oid}, sort=[("created_at", -1)])


def _aws_error(exc):
    if isinstance(exc, ClientError):
        err = exc.response["Error"]
        return err.get("Code", "Error") + ": " + err.get("Message", "")
    return "Could not reach AWS: " + type(exc).__name__


@deploy_bp.get("/api/deployments")
@token_required
def history():
    cursor = get_db().deployment_runs.find({"user_id": g.user["_id"]}).sort("created_at", -1).limit(50)
    return jsonify(runs=[public_run(_refresh(r)) for r in cursor]), 200


@deploy_bp.get("/api/projects/<project_id>/deployment")
@token_required
def get_deployment(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404
    db = get_db()
    approval = db.deployments.find_one({"project_id": project["_id"], "status": "approved"})
    run = _latest_run(project["_id"])
    events = []
    if run:
        run = _refresh(run)
        events = deployer.events(run["stack_id"], run["region"])
    return jsonify(
        project_name=project["name"],
        enabled=deployer.enabled(),
        cost_cap=deployer.cost_cap(),
        approval=public_approval(approval),
        run=public_run(run) if run else None,
        events=events,
    ), 200


@deploy_bp.post("/api/projects/<project_id>/deploy")
@token_required
def deploy(project_id):
    if not deployer.enabled():
        return jsonify(error="Deployment is switched off. Set DEPLOY_ENABLED=true in backend/.env and restart the server."), 403
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404
    data = request.get_json(silent=True) or {}
    if str(data.get("confirm_text", "")).strip() != "DEPLOY":
        return jsonify(error="Type DEPLOY to confirm."), 400

    db = get_db()
    approval = db.deployments.find_one({"project_id": project["_id"], "status": "approved"})
    if not approval:
        return jsonify(error="Approve an option first (Approval tab)."), 400
    rec_doc = db.recommendations.find_one({"project_id": project["_id"]})
    req = db.requirements.find_one({"project_id": project["_id"]})
    if not rec_doc or not req:
        return jsonify(error="Generate the recommendation first."), 400
    rec = rec_doc["result"]
    option = next((o for o in rec["options"] if o["key"] == approval["option"]["key"]), None)
    approved = approval["option"]
    if not option or (option["compute"], option["monthly_usd"]) != (approved["compute"], approved["monthly_usd"]):
        return jsonify(error="The recommendation changed after you approved it. Approve again."), 409

    cap = deployer.cost_cap()
    if option["monthly_usd"] > cap:
        return jsonify(error="Estimated $%.2f per month is above your safety cap of $%.2f (MAX_DEPLOY_MONTHLY_USD)." % (option["monthly_usd"], cap)), 400
    if db.deployment_runs.find_one({"project_id": project["_id"], "status": {"$ne": "deleted"}}):
        return jsonify(error="This project already has a stack. Delete it before deploying again."), 409

    st = aws_client.status()
    if not st["connected"]:
        return jsonify(error=st["reason"]), 400

    template = build_template(project, rec, option, req)
    issues = check_template(template)
    if issues:
        return jsonify(error="Template failed local checks: " + "; ".join(issues)), 400

    import json
    name = deployer.stack_name(project["_id"])
    tags = [{"Key": "ProjectId", "Value": str(project["_id"])}, {"Key": "ManagedBy", "Value": "cloud-recommender"}]
    try:
        stack_id = deployer.create_stack(name, json.dumps(template, separators=(",", ":")), rec["region"], tags)
    except (ClientError, BotoCoreError) as exc:
        return jsonify(error=_aws_error(exc)), 502

    now = datetime.now(timezone.utc)
    run = {
        "project_id": project["_id"],
        "user_id": g.user["_id"],
        "project_name": project["name"],
        "stack_name": name,
        "stack_id": stack_id,
        "region": rec["region"],
        "option_key": option["key"],
        "option_label": option["label"],
        "compute": option["compute"],
        "monthly_usd": option["monthly_usd"],
        "status": "creating",
        "aws_status": "CREATE_IN_PROGRESS",
        "reason": "",
        "outputs": [],
        "created_at": now,
        "updated_at": now,
    }
    run["_id"] = db.deployment_runs.insert_one(run).inserted_id
    db.projects.update_one({"_id": project["_id"]}, {"$set": {"status": "deploying"}})
    return jsonify(run=public_run(run)), 201


@deploy_bp.post("/api/projects/<project_id>/deployment/delete")
@token_required
def delete_deployment(project_id):
    project = _owned_project(project_id)
    if not project:
        return jsonify(error="Project not found."), 404
    data = request.get_json(silent=True) or {}
    if str(data.get("confirm_name", "")).strip() != project["name"]:
        return jsonify(error="Type the exact project name to delete the AWS resources."), 400
    run = _latest_run(project["_id"])
    if not run or run["status"] in ("deleted", "deleting"):
        return jsonify(error="There is no stack to delete."), 400
    try:
        deployer.delete_stack(run["stack_id"], run["region"])
    except (ClientError, BotoCoreError) as exc:
        return jsonify(error=_aws_error(exc)), 502
    get_db().deployment_runs.update_one(
        {"_id": run["_id"]},
        {"$set": {"status": "deleting", "aws_status": "DELETE_IN_PROGRESS", "updated_at": datetime.now(timezone.utc)}},
    )
    run = get_db().deployment_runs.find_one({"_id": run["_id"]})
    return jsonify(run=public_run(run)), 200
