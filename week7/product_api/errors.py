from flask import jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from .extensions import db


class ApiError(Exception):
    def __init__(self, status, error, detail):
        super().__init__(detail)
        self.status = status
        self.error = error
        self.detail = detail


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def on_api_error(err):
        db.session.rollback()
        return jsonify(error=err.error, detail=err.detail), err.status

    @app.errorhandler(HTTPException)
    def on_http_error(err):
        db.session.rollback()
        error = "validation_error" if err.code == 422 else err.name.lower().replace(" ", "_")
        body = {"error": error, "detail": err.description}
        data = getattr(err, "data", {})
        if isinstance(data, dict) and data.get("messages"):
            body["fields"] = data["messages"]
        response = jsonify(body)
        response.status_code = err.code
        for name, value in err.get_response().headers:
            if name.lower() not in {"content-type", "content-length"}:
                response.headers[name] = value
        return response

    @app.errorhandler(IntegrityError)
    def on_integrity_error(_err):
        db.session.rollback()
        return jsonify(error="conflict", detail="The request conflicts with stored data."), 409

    @app.errorhandler(SQLAlchemyError)
    def on_database_error(_err):
        db.session.rollback()
        app.logger.exception("database_error")
        return jsonify(error="internal_error", detail="An internal database error occurred."), 500

    @app.errorhandler(Exception)
    def on_unexpected_error(_err):
        db.session.rollback()
        app.logger.exception("unhandled_error")
        return jsonify(error="internal_error", detail="An unexpected error occurred."), 500
