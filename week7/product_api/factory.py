import os
from pathlib import Path

from flask import Flask
from flask_smorest import Api

from bai1_product_api.routes import blp as products_blp
from bai2_orders.routes import blp as orders_blp
from bai4_healthcheck.health import blp as health_blp

from .errors import register_error_handlers
from .extensions import db, migrate
from .logging_config import configure_logging


def create_app(config=None):
    instance = Path(os.environ.get("INSTANCE_PATH", Path.cwd() / "instance")).resolve()
    app = Flask(__name__, instance_path=str(instance), instance_relative_config=True)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DB_URL", "sqlite:///products.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        MIGRATIONS_DIR="migrations",
        LOG_LEVEL=os.environ.get("LOG_LEVEL", "INFO"),
        MAX_CONTENT_LENGTH=1_048_576,
        API_TITLE="Week 7 Product and Order API",
        API_VERSION="1.0.0",
        OPENAPI_VERSION="3.0.3",
        OPENAPI_URL_PREFIX="/",
        OPENAPI_JSON_PATH="openapi.json",
        OPENAPI_SWAGGER_UI_PATH="/docs",
        OPENAPI_SWAGGER_UI_URL="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/",
    )
    app.config.from_prefixed_env(prefix="APP")
    if config:
        app.config.from_mapping(config)
    instance.mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db, directory=app.config["MIGRATIONS_DIR"])
    api = Api(app)
    api.register_blueprint(products_blp)
    api.register_blueprint(orders_blp)
    app.register_blueprint(health_blp)
    register_error_handlers(app)
    configure_logging(app)
    return app
