import certifi
from pymongo import ASCENDING, DESCENDING, MongoClient

_client = None
_db = None


def init_db(app):
    global _client, _db
    if not app.config.get("MONGO_URI"):
        raise RuntimeError("MONGO_URI is missing. Check backend/.env")
    _client = MongoClient(
        app.config["MONGO_URI"],
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000,
    )
    _db = _client[app.config["MONGO_DB_NAME"]]

    try:
        _db.users.create_index([("email", ASCENDING)], unique=True)
        _db.projects.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        _db.requirements.create_index([("project_id", ASCENDING)], unique=True)
        _db.token_blocklist.create_index("expires_at", expireAfterSeconds=0)
    except Exception as exc:
        print("WARNING: could not create indexes:", type(exc).__name__)


def get_db():
    return _db
