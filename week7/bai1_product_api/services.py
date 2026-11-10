from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from product_api.errors import ApiError
from product_api.extensions import db
from .models import Product


def get_product(product_id):
    product = db.session.scalar(select(Product).where(
        Product.id == product_id, Product.archived.is_(False)
    ))
    if product is None:
        raise ApiError(404, "not_found", "Product not found.")
    return product


def list_products(page, size):
    active = Product.archived.is_(False)
    rows = db.session.scalars(select(Product).where(active).order_by(Product.id)
                              .offset((page - 1) * size).limit(size)).all()
    total = db.session.scalar(select(func.count()).select_from(Product).where(active))
    return {"items": rows, "page": page, "size": size, "total": total}


def create_product(data):
    product = Product(**data)
    db.session.add(product)
    try:
        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()
        raise ApiError(409, "sku_exists", "A product with this SKU already exists.") from err
    return product


def patch_product(product_id, data):
    product = get_product(product_id)
    for name, value in data.items():
        setattr(product, name, value)
    db.session.commit()
    return product


def delete_product(product_id):
    product = get_product(product_id)
    product.archived = True
    db.session.commit()


def take_stock(product_id, qty):
    # One conditional UPDATE prevents concurrent requests from overselling.
    product = db.session.scalar(update(Product).where(
        Product.id == product_id,
        Product.archived.is_(False),
        Product.qty_in_stock >= qty,
    ).values(qty_in_stock=Product.qty_in_stock - qty).returning(Product))
    if product is None:
        get_product(product_id)  # Distinguish missing/archived from insufficient stock.
        raise ApiError(409, "out_of_stock", "Insufficient stock for this product.")
    return product


def reserve_product(product_id, qty):
    product = take_stock(product_id, qty)
    db.session.commit()
    return product
