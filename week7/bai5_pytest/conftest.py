import pytest

from product_api import create_app
from product_api.extensions import db


@pytest.fixture
def app(tmp_path):
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "LOG_LEVEL": "CRITICAL",
    })
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_product(client):
    counter = 0

    def make(**overrides):
        nonlocal counter
        counter += 1
        payload = {"sku": f"SKU-{counter:03}", "name": f"Product {counter}", "price_cents": 1500, "qty_in_stock": 10}
        payload.update(overrides)
        response = client.post("/api/v1/products", json=payload)
        assert response.status_code == 201, response.json
        return response.json

    return make
