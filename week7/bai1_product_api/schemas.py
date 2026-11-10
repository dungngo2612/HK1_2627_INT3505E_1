from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from product_api.schemas import InputSchema, NonBlankString


class ProductIn(InputSchema):
    sku = NonBlankString(required=True, validate=[
        validate.Length(min=3, max=32), validate.Regexp(r"^[A-Z0-9-]+$")
    ])
    name = NonBlankString(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(allow_none=True, validate=validate.Length(max=2000))
    price_cents = fields.Integer(required=True, strict=True, validate=validate.Range(min=0, max=2_147_483_647))
    qty_in_stock = fields.Integer(load_default=0, strict=True, validate=validate.Range(min=0, max=2_147_483_647))


class ProductPatch(InputSchema):
    name = NonBlankString(validate=validate.Length(min=1, max=255))
    description = fields.String(allow_none=True, validate=validate.Length(max=2000))
    price_cents = fields.Integer(strict=True, validate=validate.Range(min=0, max=2_147_483_647))
    qty_in_stock = fields.Integer(strict=True, validate=validate.Range(min=0, max=2_147_483_647))

    @validates_schema
    def require_changes(self, data, **_kwargs):
        if not data:
            raise ValidationError("Provide at least one editable field.")


class ReserveIn(InputSchema):
    qty = fields.Integer(required=True, strict=True, validate=validate.Range(min=1, max=2_147_483_647))


class ProductOut(Schema):
    id = fields.Integer()
    sku = fields.String()
    name = fields.String()
    description = fields.String(allow_none=True)
    price_cents = fields.Integer()
    qty_in_stock = fields.Integer()
    archived = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class ProductPage(Schema):
    items = fields.List(fields.Nested(ProductOut))
    page = fields.Integer()
    size = fields.Integer()
    total = fields.Integer()
