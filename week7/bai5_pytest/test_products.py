from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from product_api import create_app
from product_api.extensions import db
from bai1_product_api.models import Product


def test_product_crud_pagination_and_soft_delete(client, make_product, app):
    first = make_product(name="First", description="Keep this description")
    second = make_product(name="Second")
    assert client.get(f'/api/v1/products/{first["id"]}').json["sku"] == first["sku"]
    page = client.get("/api/v1/products?page=2&size=1").json
    assert page["total"] == 2
    assert page["page"] == 2 and page["size"] == 1
    assert [p["id"] for p in page["items"]] == [second["id"]]

    patched = client.patch(f'/api/v1/products/{first["id"]}', json={"price_cents": 0})
    assert patched.status_code == 200
    assert patched.json["price_cents"] == 0
    assert patched.json["name"] == "First"
    assert patched.json["description"] == "Keep this description"

    deleted = client.delete(f'/api/v1/products/{first["id"]}')
    assert deleted.status_code == 204 and deleted.data == b""
    assert client.get(f'/api/v1/products/{first["id"]}').status_code == 404
    assert client.patch(f'/api/v1/products/{first["id"]}', json={"name": "Hidden"}).status_code == 404
    assert client.post(f'/api/v1/products/{first["id"]}/reserve', json={"qty": 1}).status_code == 404
    assert client.get("/api/v1/products").json["total"] == 1
    with app.app_context():
        assert db.session.get(Product, first["id"]).archived is True


def test_duplicate_sku_returns_409_and_request_afterward_still_works(client, make_product):
    original = make_product()
    duplicate = client.post("/api/v1/products", json={
        "sku": original["sku"], "name": "Duplicate", "price_cents": 1
    })
    assert duplicate.status_code == 409
    assert duplicate.json["error"] == "sku_exists"
    assert client.get("/api/v1/products").json["total"] == 1
    make_product()


@pytest.mark.parametrize("changes", [
    {"sku": "ab"}, {"sku": "has spaces"}, {"name": "   "}, {"name": "x" * 256},
    {"price_cents": -1}, {"price_cents": 1.5}, {"price_cents": True},
    {"price_cents": "123"}, {"price_cents": 2_147_483_648},
    {"qty_in_stock": -1}, {"qty_in_stock": None}, {"archived": True}, {"id": 1},
])
def test_invalid_product_input_is_422(client, changes):
    data = {"sku": "VALID-SKU", "name": "Valid", "price_cents": 100}
    data.update(changes)
    response = client.post("/api/v1/products", json=data)
    assert response.status_code == 422
    assert response.json["error"] == "validation_error"
    assert "detail" in response.json and "fields" in response.json
    assert client.get("/api/v1/products").json["total"] == 0


@pytest.mark.parametrize("body", [{}, {"sku": "NEW-SKU"}, {"archived": True}, {"name": ""}])
def test_invalid_patch_rejected(client, make_product, body):
    product = make_product()
    response = client.patch(f'/api/v1/products/{product["id"]}', json=body)
    assert response.status_code == 422


@pytest.mark.parametrize("query", ["page=0", "size=0", "size=101", "page=abc", "page=1.5", "unexpected=1"])
def test_invalid_pagination_is_422(client, query):
    assert client.get(f"/api/v1/products?{query}").status_code == 422


def test_reserve_success_and_insufficient_stock_rollback(client, make_product):
    product = make_product(qty_in_stock=3)
    path = f'/api/v1/products/{product["id"]}/reserve'
    reserved = client.post(path, json={"qty": 2})
    assert reserved.status_code == 200 and reserved.json["qty_in_stock"] == 1
    rejected = client.post(path, json={"qty": 2})
    assert rejected.status_code == 409 and rejected.json["error"] == "out_of_stock"
    assert client.get(f'/api/v1/products/{product["id"]}').json["qty_in_stock"] == 1
    assert client.post(path, json={"qty": 1}).json["qty_in_stock"] == 0
    assert client.post("/api/v1/products/999/reserve", json={"qty": 1}).status_code == 404


@pytest.mark.parametrize("qty", [0, -1, True, 1.5, "1", None])
def test_reserve_rejects_invalid_quantity(client, make_product, qty):
    product = make_product()
    assert client.post(f'/api/v1/products/{product["id"]}/reserve', json={"qty": qty}).status_code == 422


def test_concurrent_reservations_cannot_oversell(tmp_path):
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f'sqlite:///{tmp_path / "concurrent.db"}',
        "LOG_LEVEL": "CRITICAL",
    })
    with application.app_context():
        db.create_all()
        product = Product(sku="LIMITED", name="Limited stock", price_cents=100, qty_in_stock=3)
        db.session.add(product)
        db.session.commit()
        product_id = product.id

    def reserve(_number):
        with application.test_client() as connection:
            return connection.post(f"/api/v1/products/{product_id}/reserve", json={"qty": 1}).status_code

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(reserve, range(8)))
        assert statuses.count(200) == 3
        assert statuses.count(409) == 5
        with application.app_context():
            assert db.session.scalar(select(Product.qty_in_stock)) == 0
    finally:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()
