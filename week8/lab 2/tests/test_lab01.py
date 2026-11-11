"""Lab 1 tests for the Books API."""

import pytest
from jsonschema import ValidationError, validate

from tools import get_book_schema


@pytest.fixture
def book_response(client, sample_book):
    response = client.get(f"/books/{sample_book}")
    assert response.status_code == 200
    return response.get_json()


@pytest.fixture
def book_response_with_extra_field(book_response):
    return {**book_response, "password_hash": "fake-hash"}


def test_list_books_returns_empty_array(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []


def test_get_missing_book_returns_not_found(client):
    response = client.get("/books/9999")

    assert response.status_code == 404
    assert response.get_json()["code"] == "NOT_FOUND"


def test_create_book_without_title_returns_field_error(client):
    response = client.post("/books", json={"author": "J.J. Geewax"})

    assert response.status_code == 400
    assert any(error["field"] == "title" for error in response.get_json()["errors"])


def test_get_deleted_book_returns_not_found(client):
    created = client.post("/books", json={"title": "Book", "author": "Author"})
    assert created.status_code == 201
    book_id = created.get_json()["id"]

    deleted = client.delete(f"/books/{book_id}")
    assert deleted.status_code == 204

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404


def test_response_extra_field_blocked(book_response, book_response_with_extra_field):
    schema = get_book_schema()
    properties = schema["properties"]
    properties["year"]["type"] = "integer"

    for field_schema in properties.values():
        if field_schema.pop("nullable", False):
            field_schema["type"] = [field_schema["type"], "null"]

    validate(instance=book_response, schema=schema)

    with pytest.raises(ValidationError) as error:
        validate(instance=book_response_with_extra_field, schema=schema)

    assert error.value.validator == "additionalProperties"
    assert "password_hash" in error.value.message
