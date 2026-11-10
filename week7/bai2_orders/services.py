from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from bai1_product_api.services import take_stock
from product_api.errors import ApiError
from product_api.extensions import db
from .models import Order, OrderItem


def order_query():
    # Collection: selectinload; to-one Product: joinedload. Serialization needs no lazy queries.
    return select(Order).options(selectinload(Order.items).joinedload(OrderItem.product))


def get_order(order_id):
    order = db.session.scalar(order_query().where(Order.id == order_id))
    if order is None:
        raise ApiError(404, "not_found", "Order not found.")
    return order


def list_orders(page, size):
    rows = db.session.scalars(order_query().order_by(Order.id)
                              .offset((page - 1) * size).limit(size)).all()
    total = db.session.scalar(select(func.count()).select_from(Order))
    return {"items": rows, "page": page, "size": size, "total": total}


def create_order(data):
    order = Order(customer_name=data["customer_name"], items=[])
    # Consistent lock ordering reduces deadlocks when two orders share products.
    for item in sorted(data["items"], key=lambda value: value["product_id"]):
        product = take_stock(item["product_id"], item["qty"])
        order.items.append(OrderItem(
            product=product, quantity=item["qty"], unit_price_cents=product.price_cents
        ))
    db.session.add(order)
    db.session.commit()
    # Reload the whole graph explicitly after commit expires ORM attributes.
    return get_order(order.id)
