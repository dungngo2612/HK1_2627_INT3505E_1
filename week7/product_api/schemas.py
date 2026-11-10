from marshmallow import RAISE, Schema, ValidationError, fields, validate


class InputSchema(Schema):
    class Meta:
        unknown = RAISE


class NonBlankString(fields.String):
    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs).strip()
        if not value:
            raise ValidationError("Must not be blank.")
        return value


class PaginationIn(InputSchema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1, max=2_147_483_647))
    size = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))


class ErrorOut(Schema):
    error = fields.String()
    detail = fields.String()
    fields = fields.Dict()
