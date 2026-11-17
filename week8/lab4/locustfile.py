"""Weighted Books API tasks and a separate single-endpoint pool experiment."""

import random
from uuid import uuid4

from locust import HttpUser, between, task


def valid_book(book):
    return (
        isinstance(book, dict)
        and set(book) == {"id", "title", "author", "year", "isbn"}
        and type(book["id"]) is int
        and isinstance(book["title"], str)
        and isinstance(book["author"], str)
        and (book["year"] is None or type(book["year"]) is int)
        and (book["isbn"] is None or isinstance(book["isbn"], str))
    )


def check_response(response, expected_status, year=None, single=False):
    if response.status_code == 0:
        response.failure(f"Transport error: {response.error}")
        return None
    if response.status_code != expected_status:
        try:
            code = response.json().get("code", "unknown")
        except (ValueError, AttributeError):
            code = "invalid_json"
        response.failure(f"HTTP {response.status_code}: {code}")
        return None
    try:
        body = response.json()
    except ValueError:
        response.failure("Invalid JSON")
        return None
    books = [body] if single else body
    if (
        not isinstance(books, list)
        or (not single and not 1 <= len(books) <= 20)
        or not all(valid_book(book) for book in books)
        or (year is not None and any(book["year"] != year for book in books))
    ):
        response.failure("Invalid Book schema, empty fixture page, or incorrect year filter")
        return None
    return body


class BooksUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.trust_env = False

    @task(3)
    def list_books(self):
        with self.client.get(
            "/books", params={"page": random.randint(1, 50)},
            name="GET /books", timeout=5, allow_redirects=False, catch_response=True,
        ) as response:
            check_response(response, 200)

    @task(2)
    def read_book(self):
        # IDs 1..50 are seeded, so a 404 here would be a real failure.
        book_id = random.randint(1, 50)
        with self.client.get(
            f"/books/{book_id}", name="GET /books/{id}", timeout=5,
            allow_redirects=False, catch_response=True,
        ) as response:
            check_response(response, 200, single=True)

    @task(1)
    def create_book(self):
        title = f"Locust {uuid4().hex}"
        with self.client.post(
            "/books", json={"title": title, "author": "locust", "year": 2021},
            name="POST /books", timeout=5, allow_redirects=False, catch_response=True,
        ) as response:
            book = check_response(response, 201, single=True)
            if book is not None and book["title"] != title:
                response.failure("POST returned a different title")

    @task(1)
    def search_by_year(self, year=None):
        year = random.randint(2000, 2024) if year is None else year
        with self.client.get(
            "/books", params={"year": year}, name="GET /books?year={year}",
            timeout=5, allow_redirects=False, catch_response=True,
        ) as response:
            # Injected HTTP 500 responses are recorded as failures, not hidden.
            check_response(response, 200, year=year)


class PoolSearchUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.trust_env = False

    @task
    def search(self):
        year = random.randint(2000, 2024)
        with self.client.get(
            "/books", params={"year": year}, name="GET /books?year={year}",
            timeout=5, allow_redirects=False, catch_response=True,
        ) as response:
            check_response(response, 200, year=year)
