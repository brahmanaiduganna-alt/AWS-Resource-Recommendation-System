from flask import Flask, jsonify
from flask_cors import CORS
from pymongo.errors import PyMongoError

from app.config import Config
from app.extensions import init_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is missing. Check backend/.env")

    CORS(app, origins=[app.config["FRONTEND_ORIGIN"]])
    init_db(app)

    from app.routes.health import health_bp
    from app.routes.auth import auth_bp
    from app.routes.projects import projects_bp
    from app.routes.requirements import requirements_bp
    from app.routes.recommendations import recommendations_bp
    from app.routes.approval import approval_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(requirements_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(approval_bp)

    @app.errorhandler(PyMongoError)
    def database_error(exc):
        return jsonify(error="Database unavailable. Please try again."), 503

    @app.get("/")
    def index():
        return {"message": "Cloud Recommender API is running", "health": "/api/health"}

    return app
