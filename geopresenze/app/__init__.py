from flask import Flask
from flask_cors import CORS
from app.models import db

def create_app():
    app = Flask(
        __name__,
        template_folder="/content/geopresenze/templates",
        static_folder="/content/geopresenze/static"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////content/geopresenze/presenze.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "geopresenze-colab-2024"
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
