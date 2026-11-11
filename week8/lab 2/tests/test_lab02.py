"""Contract checks against real Flask responses."""

from jsonschema import validate

from tools import get_book_schema


def test_get_book_response_matches_openapi(client, sample_book):
    response = client.get(f"/books/{sample_book}")
    assert response.status_code == 200

    schema = get_book_schema()
    # JSON Schema represents OpenAPI 3.0 nullable types with a type union.
    for field_schema in schema["properties"].values():
        if field_schema.pop("nullable", False):
            field_schema["type"] = [field_schema["type"], "null"]

    validate(instance=response.get_json(), schema=schema)
