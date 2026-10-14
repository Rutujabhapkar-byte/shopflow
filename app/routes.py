from flask import Blueprint
from sqlalchemy import text
from . import db

bp = Blueprint("main", __name__)


@bp.get("/")
def home():
    return "ShopFlow is running"


@bp.get("/health")
def health():
    db.session.execute(text("SELECT 1"))  # fails if the database is unreachable
    return {"status": "ok"}, 200
