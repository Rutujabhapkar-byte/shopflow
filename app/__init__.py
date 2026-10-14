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
    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    from . import models  # noqa: F401  (so migrations can see the tables)
    from .routes import bp
    app.register_blueprint(bp)

    return app
