import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = "main.login"


def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    app.config["UPLOAD_FOLDER"] = os.getenv(
        "UPLOAD_FOLDER",
        os.path.abspath(os.path.join(app.root_path, os.pardir, "uploads")),
    )
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB uploads
    if config:
        app.config.update(config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    app.jinja_env.filters["inr"] = lambda paise: f"₹{paise / 100:,.2f}"

    from . import models  # noqa: F401  (so migrations can see the tables)
    from .cli import register_cli
    from .routes import bp

    app.register_blueprint(bp)
    register_cli(app)

    return app
