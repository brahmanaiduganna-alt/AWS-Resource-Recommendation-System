import json

from flask import Blueprint, jsonify, request

from app.extensions import get_db
from app.routes.requirements import _owned_project
from app.services import aws_client
from app.services.cfn_template import build_template, check_template, summarize
from app.utils.auth import token_required

templates_bp = Blueprint("templates", __name__)


def _load(project_id, option_key):
    project = _owned_project(project_id)
    if not project:
        return None, (jsonify(error="Project not found."), 404)
    db = get_db()
    rec_doc = db.recommendations.find_one({"project_id": project["_id"]})
    req = db.requirements.find_one({"project_id": project["_id"]})
    if not rec_doc or not req:
        return None, (jsonify(error="Generate the recommendation first."), 400)
    rec = rec_doc["result"]
    option = next((o for o in rec["options"] if o["key"] == option_key), None)
    if not option:
        return None, (jsonify(error="Choose one of the recommended options."), 400)
    return (project, rec, option, req), None


@templates_bp.get("/api/aws/status")
@token_required
def aws_status():
    return jsonify(aws_client.status()), 200


@templates_bp.get("/api/projects/<project_id>/template")
@token_required
def get_template(project_id):
    ctx, err = _load(project_id, request.args.get("option", ""))
    if err:
        return err
    project, rec, option, req = ctx
    template = build_template(project, rec, option, req)
    compact = json.dumps(template, separators=(",", ":"))
    return jsonify(
        option_key=option["key"],
        option_label=option["label"],
        region=rec["region"],
        monthly_usd=option["monthly_usd"],
        template=json.dumps(template, indent=2),
        resources=summarize(template),
        size_bytes=len(compact.encode("utf-8")),
    ), 200


@templates_bp.post("/api/projects/<project_id>/template/validate")
@token_required
def validate(project_id):
    data = request.get_json(silent=True) or {}
    ctx, err = _load(project_id, str(data.get("option_key", "")))
    if err:
        return err
    project, rec, option, req = ctx
    template = build_template(project, rec, option, req)
    issues = check_template(template)
    if issues:
        aws = {"status": "skipped", "message": "Fix the local problems first."}
    else:
        compact = json.dumps(template, separators=(",", ":"))
        aws = aws_client.validate_template(compact, rec["region"])
    return jsonify(local={"ok": not issues, "issues": issues}, aws=aws), 200
