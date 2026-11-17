"""Lab-only additions around the unchanged lecturer's Books API starter."""

import os
from pathlib import Path
import random
import threading
import time

from flask import g, jsonify, request
from sqlalchemy import event
from sqlalchemy.exc import TimeoutError as PoolTimeout

from app import create_app as create_starter_app
from models import db


def create_app(overrides=None):
    database = Path(os.environ.get("LAB4_DB_PATH", Path(__file__).parent / "instance/books.db")).resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_size": int(os.environ.get("LAB4_POOL_SIZE", "5")),
            "max_overflow": 0,
            "pool_timeout": int(os.environ.get("LAB4_POOL_TIMEOUT", "1")),
            "connect_args": {"timeout": 5},
        },
        "LAB4_FAILURE_RATE": float(os.environ.get("LAB4_FAILURE_RATE", "0.01")),
        "LAB4_HOLD_MS": float(os.environ.get("LAB4_HOLD_MS", "0")),
    }
    config.update(overrides or {})
    app = create_starter_app(config)
    if not 0 <= app.config["LAB4_FAILURE_RATE"] <= 1:
        raise ValueError("LAB4_FAILURE_RATE must be between 0 and 1")
    lock = threading.Lock()
    metrics = {
        "pid": os.getpid(), "active_connections": 0, "max_active_connections": 0,
        "checkouts": 0, "pool_timeouts": 0, "max_pool_wait_ms": 0.0,
        "pool_wait_total_ms": 0.0, "pool_acquire_attempts": 0, "injected_500": 0,
        "pool_size": config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_size"],
        "hold_ms": app.config["LAB4_HOLD_MS"],
    }

    with app.app_context():
        @event.listens_for(db.engine, "checkout")
        def on_checkout(*_):
            with lock:
                metrics["checkouts"] += 1
                metrics["active_connections"] += 1
                metrics["max_active_connections"] = max(
                    metrics["max_active_connections"], metrics["active_connections"]
                )

        @event.listens_for(db.engine, "checkin")
        def on_checkin(*_):
            with lock:
                metrics["active_connections"] -= 1

    def record_wait(started):
        elapsed = (time.perf_counter() - started) * 1000
        g.pool_wait_ms = elapsed
        with lock:
            metrics["pool_acquire_attempts"] += 1
            metrics["pool_wait_total_ms"] += elapsed
            metrics["max_pool_wait_ms"] = max(metrics["max_pool_wait_ms"], elapsed)

    @app.before_request
    def lab_experiments():
        if request.method != "GET" or request.path != "/books":
            return None
        if request.args.get("year") is not None and random.random() < app.config["LAB4_FAILURE_RATE"]:
            with lock:
                metrics["injected_500"] += 1
            return jsonify(code="INJECTED_FAILURE", message="Lab 4 simulated HTTP 500"), 500, {
                "X-Lab-Injected": "true",
            }
        # The pool bonus deliberately holds a real checked-out connection.
        # A/B/C use hold_ms=0 and do not execute this extra acquisition/sleep.
        if app.config["LAB4_HOLD_MS"] > 0:
            started = time.perf_counter()
            try:
                db.session.connection()
            finally:
                record_wait(started)
            time.sleep(app.config["LAB4_HOLD_MS"] / 1000)
        return None

    @app.errorhandler(PoolTimeout)
    def pool_timeout(_error):
        with lock:
            metrics["pool_timeouts"] += 1
        return jsonify(code="POOL_TIMEOUT", message="No database connection available before timeout"), 503

    @app.after_request
    def pool_wait_header(response):
        if hasattr(g, "pool_wait_ms"):
            response.headers["X-Lab-Pool-Wait-Ms"] = f"{g.pool_wait_ms:.3f}"
        return response

    @app.get("/lab/metrics")
    def lab_metrics():
        # Bonus runs have exactly one worker so these counters cover the server.
        with lock:
            snapshot = dict(metrics)
        attempts = snapshot["pool_acquire_attempts"]
        snapshot["mean_pool_wait_ms"] = snapshot["pool_wait_total_ms"] / attempts if attempts else 0
        return jsonify(snapshot)

    return app
