from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from product_api.extensions import db

blp = Blueprint("health", __name__)


@blp.get("/healthz")
def liveness():
    """Process liveness must not depend on the database."""
    return jsonify(status="ok"), 200


@blp.get("/ready")
def readiness():
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.warning("readiness_failed")
        return jsonify(status="degraded", checks={"db": "err"}), 503
    return jsonify(status="ok", checks={"db": "ok"}), 200
