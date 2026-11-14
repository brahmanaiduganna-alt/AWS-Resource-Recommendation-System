import re
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import get_db
from app.models.user import public_user
from app.utils.auth import create_token, token_required

auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _password_problem(password):
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    return None


@auth_bp.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not 2 <= len(name) <= 80:
        return jsonify(error="Name must be 2 to 80 characters."), 400
    if not EMAIL_RE.match(email):
        return jsonify(error="Enter a valid email address."), 400
    problem = _password_problem(password)
    if problem:
        return jsonify(error=problem), 400

    user = {
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "organization": "",
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = get_db().users.insert_one(user)
    except DuplicateKeyError:
        return jsonify(error="An account with this email already exists."), 409

    user["_id"] = result.inserted_id
    return jsonify(token=create_token(user["_id"]), user=public_user(user)), 201


@auth_bp.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    user = get_db().users.find_one({"email": email})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Incorrect email or password."), 401

    return jsonify(token=create_token(user["_id"]), user=public_user(user)), 200


@auth_bp.post("/api/auth/logout")
@token_required
def logout():
    exp = datetime.fromtimestamp(g.token_data["exp"], tz=timezone.utc)
    get_db().token_blocklist.insert_one({"jti": g.token_data["jti"], "expires_at": exp})
    return jsonify(message="Logged out."), 200


@auth_bp.get("/api/auth/me")
@token_required
def me():
    return jsonify(user=public_user(g.user)), 200


@auth_bp.put("/api/auth/me")
@token_required
def update_profile():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    organization = str(data.get("organization", "")).strip()

    if not 2 <= len(name) <= 80:
        return jsonify(error="Name must be 2 to 80 characters."), 400
    if len(organization) > 100:
        return jsonify(error="Organization must be at most 100 characters."), 400

    db = get_db()
    db.users.update_one(
        {"_id": g.user["_id"]}, {"$set": {"name": name, "organization": organization}}
    )
    return jsonify(user=public_user(db.users.find_one({"_id": g.user["_id"]}))), 200


@auth_bp.post("/api/auth/change-password")
@token_required
def change_password():
    data = request.get_json(silent=True) or {}
    current = str(data.get("current_password", ""))
    new = str(data.get("new_password", ""))

    if not check_password_hash(g.user["password_hash"], current):
        return jsonify(error="Current password is incorrect."), 400
    problem = _password_problem(new)
    if problem:
        return jsonify(error=problem), 400

    get_db().users.update_one(
        {"_id": g.user["_id"]},
        {"$set": {"password_hash": generate_password_hash(new)}},
    )
    return jsonify(message="Password changed."), 200
