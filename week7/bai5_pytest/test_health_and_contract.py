import json
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from product_api.extensions import db
from product_api.logging_config import JsonFormatter


def test_liveness_does_not_touch_database_but_readiness_does(client):
    with patch.object(db.session, "execute", side_effect=SQLAlchemyError("unavailable")):
        alive = client.get("/healthz")
        assert alive.status_code == 200 and alive.json == {"status": "ok"}
        ready = client.get("/ready")
        assert ready.status_code == 503 and ready.json["checks"]["db"] == "err"
    assert client.get("/ready").status_code == 200


def test_malformed_json_unknown_route_and_method_use_json_errors(client):
    response = client.post("/api/v1/products", data="{bad", content_type="application/json")
    assert response.status_code == 400
    assert set(response.json) >= {"error", "detail"}
    response = client.get("/does-not-exist")
    assert response.status_code == 404 and response.is_json
    response = client.put("/api/v1/products", json={})
    assert response.status_code == 405 and "Allow" in response.headers


def test_openapi_documents_all_business_endpoints(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json
    assert spec["openapi"] == "3.0.3"
    expected = {
        "/api/v1/products": {"get", "post"},
        "/api/v1/products/{product_id}": {"get", "patch", "delete"},
        "/api/v1/products/{product_id}/reserve": {"post"},
        "/api/v1/orders": {"get", "post"},
        "/api/v1/orders/{order_id}": {"get"},
    }
    for path, methods in expected.items():
        assert methods <= spec["paths"][path].keys()
    assert client.get("/docs").status_code == 200


def test_request_id_is_preserved_and_logs_include_latency(client, app):
    records = []
    handler = app.logger.handlers[0]
    with patch.object(handler, "emit", side_effect=records.append):
        app.logger.setLevel("INFO")
        response = client.get("/healthz", headers={"X-Request-ID": "test-request-123"})
    assert response.headers["X-Request-ID"] == "test-request-123"
    payload = json.loads(JsonFormatter().format(records[-1]))
    assert payload["event"] == "request_completed" and payload["status"] == 200
    assert payload["method"] == "GET" and payload["latency_ms"] >= 0
