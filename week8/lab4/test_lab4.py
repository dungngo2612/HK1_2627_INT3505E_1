"""Verify real server-side injection and real connection-pool exhaustion."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from benchmark_app import create_app
from models import Book, db


@pytest.fixture
def make_app(tmp_path):
    counter = 0

    def factory(**config):
        nonlocal counter
        counter += 1
        app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / f'test-{counter}.db'}",
            "LAB4_FAILURE_RATE": 0,
            **config,
        })
        with app.app_context():
            db.session.add_all([
                Book(title="A", author="X", year=2021),
                Book(title="B", author="Y", year=2022),
            ])
            db.session.commit()
        return app

    return factory


def test_search_filter_and_non_injected_requests(make_app):
    app = make_app()
    client = app.test_client()
    response = client.get("/books?year=2021")
    assert response.status_code == 200
    assert [book["title"] for book in response.json] == ["A"]
    assert client.get("/lab/metrics").json["injected_500"] == 0


def test_injection_is_real_http_500_and_only_affects_year_search(make_app):
    app = make_app(LAB4_FAILURE_RATE=1)
    client = app.test_client()
    response = client.get("/books?year=2021")
    assert response.status_code == 500
    assert response.json["code"] == "INJECTED_FAILURE"
    assert response.headers["X-Lab-Injected"] == "true"
    assert client.get("/books").status_code == 200
    assert client.get("/books/1").status_code == 200
    assert client.get("/lab/metrics").json["injected_500"] == 1


def test_real_pool_timeout_returns_503_and_releases_connections(make_app):
    app = make_app(
        SQLALCHEMY_ENGINE_OPTIONS={"pool_size": 1, "max_overflow": 0, "pool_timeout": 1},
        LAB4_HOLD_MS=1,
    )
    # Keep the sole real DB connection checked out in this thread.
    with app.app_context():
        db.session.connection()
        with ThreadPoolExecutor(max_workers=1) as executor:
            response = executor.submit(lambda: app.test_client().get("/books?year=2021")).result()
        assert response.status_code == 503
        assert response.json["code"] == "POOL_TIMEOUT"
        assert float(response.headers["X-Lab-Pool-Wait-Ms"]) >= 900
    client = app.test_client()
    assert client.get("/books?year=2021").status_code == 200
    metrics = client.get("/lab/metrics").json
    assert metrics["pool_timeouts"] == 1
    assert metrics["max_active_connections"] == 1
    assert metrics["active_connections"] == 0


def test_starter_crud_survives_benchmark_wrapper(make_app):
    client = make_app().test_client()
    created = client.post("/books", json={"title": "New", "author": "Tester", "year": 2020})
    assert created.status_code == 201
    bid = created.json["id"]
    updated = client.put(f"/books/{bid}", json={"title": "Renamed", "author": "Tester"})
    assert updated.status_code == 200 and updated.json["year"] is None
    assert client.delete(f"/books/{bid}").status_code == 204
    assert client.get(f"/books/{bid}").status_code == 404
