from flask.views import MethodView
from flask_smorest import Blueprint
from marshmallow import RAISE

from . import services
from product_api.schemas import ErrorOut, PaginationIn
from .schemas import ProductIn, ProductOut, ProductPage, ProductPatch, ReserveIn

blp = Blueprint("products", __name__, url_prefix="/api/v1/products", description="Product CRUD and stock reservations")


@blp.route("")
class ProductCollection(MethodView):
    @blp.arguments(PaginationIn, location="query", unknown=RAISE)
    @blp.response(200, ProductPage)
    @blp.alt_response(422, schema=ErrorOut)
    def get(self, query):
        """List active products with pagination."""
        return services.list_products(**query)

    @blp.arguments(ProductIn)
    @blp.response(201, ProductOut)
    @blp.alt_response(409, schema=ErrorOut)
    @blp.alt_response(422, schema=ErrorOut)
    def post(self, data):
        """Create a product with a unique SKU."""
        return services.create_product(data)


@blp.route("/<int:product_id>")
class ProductDetail(MethodView):
    @blp.response(200, ProductOut)
    @blp.alt_response(404, schema=ErrorOut)
    def get(self, product_id):
        """Get an active product."""
        return services.get_product(product_id)

    @blp.arguments(ProductPatch)
    @blp.response(200, ProductOut)
    @blp.alt_response(404, schema=ErrorOut)
    @blp.alt_response(422, schema=ErrorOut)
    def patch(self, data, product_id):
        """Change only supplied fields; SKU is immutable."""
        return services.patch_product(product_id, data)

    @blp.response(204)
    @blp.alt_response(404, schema=ErrorOut)
    def delete(self, product_id):
        """Soft-delete a product without deleting order history."""
        services.delete_product(product_id)


@blp.route("/<int:product_id>/reserve")
class ProductReservation(MethodView):
    @blp.arguments(ReserveIn)
    @blp.response(200, ProductOut)
    @blp.alt_response(404, schema=ErrorOut)
    @blp.alt_response(409, schema=ErrorOut)
    @blp.alt_response(422, schema=ErrorOut)
    def post(self, data, product_id):
        """Reserve stock atomically; the remaining quantity cannot be negative."""
        return services.reserve_product(product_id, data["qty"])
