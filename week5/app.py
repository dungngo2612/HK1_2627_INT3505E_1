"""Bookstore API: offset and keyset cursor pagination for the books resource."""

import base64
import binascii
import json
import os

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, func, or_, select


db = SQLAlchemy()


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    genre = db.Column(db.String(80), nullable=False, index=True)
    isbn = db.Column(db.String(13), nullable=False, unique=True)
    price_vnd = db.Column(db.Integer, nullable=False)
    published_year = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "genre": self.genre,
            "isbn": self.isbn,
            "price_vnd": self.price_vnd,
            "published_year": self.published_year,
        }


ALLOWED_SORT_FIELDS = {
    "id": Book.id,
    "title": Book.title,
    "author": Book.author,
    "genre": Book.genre,
    "price_vnd": Book.price_vnd,
    "published_year": Book.published_year,
}
DEFAULT_SORT = "-id"
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

SAMPLE_BOOKS = [
    {
        "title": "Designing Data-Intensive Applications",
        "author": "Martin Kleppmann",
        "genre": "technology",
        "isbn": "9781449373320",
        "price_vnd": 620000,
        "published_year": 2017,
    },
    {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "genre": "technology",
        "isbn": "9780132350884",
        "price_vnd": 450000,
        "published_year": 2008,
    },
    {
        "title": "The Pragmatic Programmer",
        "author": "David Thomas",
        "genre": "technology",
        "isbn": "9780135957059",
        "price_vnd": 510000,
        "published_year": 2019,
    },
    {
        "title": "Fluent Python",
        "author": "Luciano Ramalho",
        "genre": "technology",
        "isbn": "9781492056355",
        "price_vnd": 620000,
        "published_year": 2022,
    },
    {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "genre": "fiction",
        "isbn": "9780547928227",
        "price_vnd": 320000,
        "published_year": 1937,
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "genre": "fiction",
        "isbn": "9780141439518",
        "price_vnd": 180000,
        "published_year": 1813,
    },
    {
        "title": "Atomic Habits",
        "author": "James Clear",
        "genre": "self-help",
        "isbn": "9780735211292",
        "price_vnd": 290000,
        "published_year": 2018,
    },
    {
        "title": "The Psychology of Money",
        "author": "Morgan Housel",
        "genre": "business",
        "isbn": "9780857197689",
        "price_vnd": 260000,
        "published_year": 2020,
    },
]


def create_app(test_config=None):
    app = Flask(__name__)
    app.json.sort_keys = False
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///bookstore.sqlite3"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SEED_BOOKS=True,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        db.create_all()
        if app.config["SEED_BOOKS"] and db.session.scalar(
            select(func.count()).select_from(Book)
        ) == 0:
            db.session.add_all(Book(**book) for book in SAMPLE_BOOKS)
            db.session.commit()

    @app.get("/api/v1/books")
    @app.get("/books")
    def list_books():
        strategy = request.args.get("strategy", "cursor").strip().lower()
        if strategy not in {"offset", "cursor"}:
            return api_error(
                "invalid-strategy", "strategy must be 'offset' or 'cursor'."
            )

        limit, error = parse_limit()
        if error:
            return error

        sort_specs, sort_key, error = parse_sort()
        if error:
            return error

        genre = request.args.get("genre")
        if genre is not None:
            genre = genre.strip().lower()
            if not genre:
                return api_error("invalid-genre", "genre cannot be empty.")

        query = select(Book)
        if genre is not None:
            query = query.where(func.lower(Book.genre) == genre)

        ordered_specs = list(sort_specs)
        if "id" not in {field for field, _descending in ordered_specs}:
            # A unique tie-breaker makes every sort order deterministic.
            ordered_specs.append(("id", False))
        order_expressions = [
            ALLOWED_SORT_FIELDS[field].desc()
            if descending
            else ALLOWED_SORT_FIELDS[field].asc()
            for field, descending in ordered_specs
        ]

        if strategy == "offset":
            offset, error = parse_offset()
            if error:
                return error

            total = db.session.scalar(
                select(func.count()).select_from(query.order_by(None).subquery())
            )
            books = db.session.scalars(
                query.order_by(*order_expressions).offset(offset).limit(limit)
            ).all()
            has_more = offset + len(books) < total
            next_offset = offset + len(books) if has_more else None
            return jsonify(
                {
                    "data": [book.to_dict() for book in books],
                    "page": {
                        "strategy": "offset",
                        "offset": offset,
                        "limit": limit,
                        "total": total,
                        "has_more": has_more,
                        "next_offset": next_offset,
                    },
                }
            )

        raw_cursor = request.args.get("cursor")
        cursor_values, error = decode_cursor(
            raw_cursor, sort_key, genre, ordered_specs
        )
        if error:
            return error
        if cursor_values is not None:
            query = query.where(build_after_condition(ordered_specs, cursor_values))

        rows = db.session.scalars(
            query.order_by(*order_expressions).limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        books = rows[:limit]
        next_cursor = (
            encode_cursor(books[-1], sort_key, genre, ordered_specs)
            if books and has_more
            else None
        )
        return jsonify(
            {
                "data": [book.to_dict() for book in books],
                "page": {
                    "strategy": "cursor",
                    "limit": limit,
                    "has_more": has_more,
                    "next_cursor": next_cursor,
                },
            }
        )

    @app.errorhandler(404)
    def not_found(_error):
        return api_error("not-found", "The requested resource was not found.", 404)

    return app


def api_error(code, message, status=400):
    return jsonify({"error": {"code": code, "message": message}}), status


def parse_limit():
    raw_limit = request.args.get("limit", str(DEFAULT_LIMIT))
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return None, api_error("invalid-limit", "limit must be an integer.")
    if not 1 <= limit <= MAX_LIMIT:
        return None, api_error(
            "invalid-limit", f"limit must be between 1 and {MAX_LIMIT}."
        )
    return limit, None


def parse_offset():
    raw_offset = request.args.get("offset", "0")
    try:
        offset = int(raw_offset)
    except (TypeError, ValueError):
        return None, api_error("invalid-offset", "offset must be an integer.")
    if offset < 0:
        return None, api_error("invalid-offset", "offset cannot be negative.")
    return offset, None


def parse_sort():
    raw_sort = request.args.get("sort", DEFAULT_SORT)
    sort_specs = []
    seen = set()

    for raw_part in raw_sort.split(","):
        part = raw_part.strip()
        descending = part.startswith("-")
        field = part[1:] if descending else part
        if not field or field not in ALLOWED_SORT_FIELDS or field in seen:
            allowed = ", ".join(sorted(ALLOWED_SORT_FIELDS))
            return None, None, api_error(
                "invalid-sort",
                f"sort must contain unique allowed fields: {allowed}; prefix a field with '-' for descending order.",
            )
        seen.add(field)
        sort_specs.append((field, descending))

    canonical_sort = ",".join(
        f"-{field}" if descending else field for field, descending in sort_specs
    )
    return sort_specs, canonical_sort, None


def encode_cursor(book, sort_key, genre, ordered_specs):
    payload = {
        "sort": sort_key,
        "genre": genre,
        "values": [getattr(book, field) for field, _descending in ordered_specs],
    }
    raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw_json).decode("ascii").rstrip("=")


def decode_cursor(raw_cursor, sort_key, genre, ordered_specs):
    if raw_cursor is None:
        return None, None

    try:
        if not raw_cursor or len(raw_cursor) > 4096:
            raise ValueError
        padded = raw_cursor + ("=" * (-len(raw_cursor) % 4))
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
        payload = json.loads(decoded.decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"sort", "genre", "values"}:
            raise ValueError
        if payload["sort"] != sort_key or payload["genre"] != genre:
            raise ValueError
        values = payload["values"]
        if not isinstance(values, list) or len(values) != len(ordered_specs):
            raise ValueError

        for (field, _descending), value in zip(ordered_specs, values):
            if field in {"id", "price_vnd", "published_year"}:
                if type(value) is not int:
                    raise ValueError
            elif not isinstance(value, str):
                raise ValueError
        return values, None
    except (
        ValueError,
        TypeError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
        RecursionError,
    ):
        return None, api_error(
            "invalid-cursor", "cursor is invalid for the current sort and genre."
        )


def build_after_condition(ordered_specs, values):
    """Build a lexicographic keyset predicate for mixed sort directions."""
    clauses = []
    equal_prefix = []
    for (field, descending), value in zip(ordered_specs, values):
        column = ALLOWED_SORT_FIELDS[field]
        after = column < value if descending else column > value
        clauses.append(and_(*equal_prefix, after) if equal_prefix else after)
        equal_prefix.append(column == value)
    return or_(*clauses)


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
