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
    from app.routes.templates import templates_bp
    from app.routes.deploy import deploy_bp
    from app.routes.assistant import assistant_bp
    from app.routes.monitoring import monitoring_bp
    from app.routes.settings import settings_bp

    for bp in (health_bp, auth_bp, projects_bp, requirements_bp, recommendations_bp,
               approval_bp, templates_bp, deploy_bp, assistant_bp, monitoring_bp, settings_bp):
        app.register_blueprint(bp)

    @app.errorhandler(PyMongoError)
    def database_error(exc):
        return jsonify(error="Database unavailable. Please try again."), 503

    @app.get("/")
    def index():
        return {"message": "Cloud Recommender API is running", "health": "/api/health"}

    return app
