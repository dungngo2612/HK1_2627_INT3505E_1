import pytest
from sqlalchemy import event, func, select

from product_api.extensions import db
from bai2_orders.models import Order, OrderItem


def test_order_contains_multiple_products_and_snapshots_prices(client, make_product):
    first = make_product(price_cents=1200, qty_in_stock=10)
    second = make_product(price_cents=500, qty_in_stock=5)
    response = client.post("/api/v1/orders", json={
        "customer_name": "Nguyen Van A",
        "items": [{"product_id": first["id"], "qty": 2}, {"product_id": second["id"], "qty": 3}],
    })
    assert response.status_code == 201, response.json
    order = response.json
    assert len(order["items"]) == 2
    assert order["total_cents"] == 3900
    assert order["items"][0]["product"]["sku"] == first["sku"]
    assert client.get(f'/api/v1/products/{first["id"]}').json["qty_in_stock"] == 8
    assert client.get(f'/api/v1/products/{second["id"]}').json["qty_in_stock"] == 2

    client.patch(f'/api/v1/products/{first["id"]}', json={"price_cents": 9999})
    client.delete(f'/api/v1/products/{second["id"]}')
    saved = client.get(f'/api/v1/orders/{order["id"]}')
    assert saved.status_code == 200
    assert saved.json["total_cents"] == 3900
    assert saved.json["items"][1]["product"]["archived"] is True


@pytest.mark.parametrize("second_exists", [True, False])
def test_order_failure_rolls_back_all_items_and_stock(client, make_product, app, second_exists):
    first = make_product(qty_in_stock=5)
    second_id = make_product(qty_in_stock=0)["id"] if second_exists else 999
    response = client.post("/api/v1/orders", json={
        "customer_name": "Rollback test",
        "items": [{"product_id": first["id"], "qty": 2}, {"product_id": second_id, "qty": 1}],
    })
    assert response.status_code == (409 if second_exists else 404)
    assert client.get(f'/api/v1/products/{first["id"]}').json["qty_in_stock"] == 5
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Order)) == 0
        assert db.session.scalar(select(func.count()).select_from(OrderItem)) == 0


@pytest.mark.parametrize("payload", [
    {"customer_name": "A", "items": []},
    {"customer_name": " ", "items": [{"product_id": 1, "qty": 1}]},
    {"customer_name": "A", "items": [{"product_id": 1, "qty": 0}]},
    {"customer_name": "A", "items": [{"product_id": 1, "qty": 1, "unit_price_cents": 0}]},
    {"customer_name": "A", "items": [{"product_id": 1, "qty": 1}, {"product_id": 1, "qty": 2}]},
    {"customer_name": "A", "product_id": 1},
])
def test_order_validation(client, payload):
    assert client.post("/api/v1/orders", json=payload).status_code == 422


def test_orders_use_constant_query_count_with_eager_loading(client, make_product, app):
    first = make_product(qty_in_stock=100)
    second = make_product(qty_in_stock=100)

    def create_order(number):
        response = client.post("/api/v1/orders", json={
            "customer_name": f"Customer {number}",
            "items": [{"product_id": first["id"], "qty": 1}, {"product_id": second["id"], "qty": 1}],
        })
        assert response.status_code == 201, response.json

    def measure_queries():
        statements = []

        def record(_conn, _cursor, statement, _params, _context, _many):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        with app.app_context():
            engine = db.engine
        event.listen(engine, "before_cursor_execute", record)
        try:
            response = client.get("/api/v1/orders?size=100")
        finally:
            event.remove(engine, "before_cursor_execute", record)
        assert response.status_code == 200
        assert all(len(order["items"]) == 2 for order in response.json["items"])
        return len(statements), response.json

    create_order(1)
    first_count, one = measure_queries()
    assert one["total"] == 1
    for number in range(2, 11):
        create_order(number)
    many_count, many = measure_queries()
    assert many["total"] == 10
    # Orders, items JOIN products, and total count: exactly 3 SELECTs in both cases.
    assert first_count == many_count == 3


def test_orders_pagination_and_missing_order(client, make_product):
    product = make_product()
    for number in range(3):
        assert client.post("/api/v1/orders", json={
            "customer_name": f"Customer {number}", "items": [{"product_id": product["id"], "qty": 1}]
        }).status_code == 201
    page = client.get("/api/v1/orders?page=2&size=2").json
    assert page["total"] == 3 and len(page["items"]) == 1
    assert page["items"][0]["customer_name"] == "Customer 2"
    assert client.get("/api/v1/orders/999").status_code == 404
