from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.extensions import init_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, origins=[app.config["FRONTEND_ORIGIN"]])
    init_db(app)

    from app.routes.health import health_bp
    app.register_blueprint(health_bp)

    @app.get("/")
    def index():
        return {"message": "Cloud Recommender API is running", "health": "/api/health"}

    return app
