import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from bson import ObjectId
from flask import current_app, g, jsonify, request

from app.extensions import get_db


def create_token(user_id):
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=current_app.config["JWT_EXPIRY_HOURS"])
    payload = {
        "sub": str(user_id),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": expires,
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    return token


def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Please log in first."), 401
        token = header[7:]
        try:
            data = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            return jsonify(error="Session expired. Please log in again."), 401
        except jwt.InvalidTokenError:
            return jsonify(error="Invalid session. Please log in again."), 401

        db = get_db()
        if db.token_blocklist.find_one({"jti": data["jti"]}):
            return jsonify(error="You are logged out. Please log in again."), 401
        user = db.users.find_one({"_id": ObjectId(data["sub"])})
        if not user:
            return jsonify(error="Account not found."), 401

        g.user = user
        g.token_data = data
        return fn(*args, **kwargs)

    return wrapper
