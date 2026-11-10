from flask.views import MethodView
from flask_smorest import Blueprint
from marshmallow import RAISE

from . import services
from product_api.schemas import ErrorOut, PaginationIn
from .schemas import OrderIn, OrderOut, OrderPage

blp = Blueprint("orders", __name__, url_prefix="/api/v1/orders", description="Orders with multiple product line items")


@blp.route("")
class OrderCollection(MethodView):
    @blp.arguments(PaginationIn, location="query", unknown=RAISE)
    @blp.response(200, OrderPage)
    @blp.alt_response(422, schema=ErrorOut)
    def get(self, query):
        """List orders and eager-load items/products to avoid N+1 queries."""
        return services.list_orders(**query)

    @blp.arguments(OrderIn)
    @blp.response(201, OrderOut)
    @blp.alt_response(404, schema=ErrorOut)
    @blp.alt_response(409, schema=ErrorOut)
    @blp.alt_response(422, schema=ErrorOut)
    def post(self, data):
        """Create all order items and deduct stock in one transaction."""
        return services.create_order(data)


@blp.route("/<int:order_id>")
class OrderDetail(MethodView):
    @blp.response(200, OrderOut)
    @blp.alt_response(404, schema=ErrorOut)
    def get(self, order_id):
        """Get an order including its items and product summaries."""
        return services.get_order(order_id)
