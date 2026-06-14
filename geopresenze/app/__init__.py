import os
from flask import Flask
from flask_cors import CORS
from app.models import db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static")
    )

    db_path = os.environ.get("DATABASE_URL",
                  f"sqlite:///{os.path.join(BASE_DIR, 'presenze.db')}")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "geopresenze-2024")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    db.init_app(app)
    CORS(app)

    with app.app_context():
        db.create_all()
        from app.routes.attend import attend_bp
        from app.routes.admin import admin_bp
        app.register_blueprint(attend_bp)
        app.register_blueprint(admin_bp)

    return app
