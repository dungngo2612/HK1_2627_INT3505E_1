from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from product_api.schemas import InputSchema, NonBlankString


class OrderItemIn(InputSchema):
    product_id = fields.Integer(required=True, strict=True, validate=validate.Range(min=1, max=2_147_483_647))
    qty = fields.Integer(required=True, strict=True, validate=validate.Range(min=1, max=2_147_483_647))


class OrderIn(InputSchema):
    customer_name = NonBlankString(required=True, validate=validate.Length(min=1, max=255))
    items = fields.List(fields.Nested(OrderItemIn), required=True, validate=validate.Length(min=1, max=100))

    @validates_schema
    def no_duplicate_products(self, data, **_kwargs):
        identifiers = [item["product_id"] for item in data["items"]]
        if len(identifiers) != len(set(identifiers)):
            raise ValidationError("Each product may appear only once.", field_name="items")


class ProductSummary(Schema):
    id = fields.Integer()
    sku = fields.String()
    name = fields.String()
    archived = fields.Boolean()


class OrderItemOut(Schema):
    id = fields.Integer()
    product_id = fields.Integer()
    qty = fields.Integer(attribute="quantity")
    unit_price_cents = fields.Integer()
    line_total_cents = fields.Integer()
    product = fields.Nested(ProductSummary)


class OrderOut(Schema):
    id = fields.Integer()
    customer_name = fields.String()
    created_at = fields.DateTime()
    items = fields.List(fields.Nested(OrderItemOut))
    total_cents = fields.Integer()


class OrderPage(Schema):
    items = fields.List(fields.Nested(OrderOut))
    page = fields.Integer()
    size = fields.Integer()
    total = fields.Integer()
