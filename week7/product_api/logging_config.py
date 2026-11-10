import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from flask import g, has_request_context, request


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        if has_request_context():
            payload["request_id"] = g.get("request_id", "-")
        for key in ("method", "path", "status", "latency_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app.logger.handlers = [handler]
    app.logger.propagate = False
    app.logger.setLevel(app.config["LOG_LEVEL"])

    @app.before_request
    def start_request():
        value = request.headers.get("X-Request-ID", "")
        g.request_id = value if 0 < len(value) <= 128 and value.isascii() and value.isprintable() else str(uuid.uuid4())
        g.started_at = time.perf_counter()

    @app.after_request
    def finish_request(response):
        response.headers["X-Request-ID"] = g.request_id
        app.logger.info("request_completed", extra={
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "latency_ms": round((time.perf_counter() - g.started_at) * 1000, 3),
        })
        return response
