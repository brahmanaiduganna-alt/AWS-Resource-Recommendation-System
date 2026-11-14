import certifi
from pymongo import MongoClient

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


def get_db():
    return _db
