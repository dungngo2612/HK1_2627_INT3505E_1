# app.py - bai tap buoi 2

from flask import Flask, jsonify, request, make_response
import sqlite3
import os

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "bookstore.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                isbn TEXT,
                price REAL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (book_id) REFERENCES books(id)
            );
        """)


init_db()


@app.errorhandler(404)
def not_found(e):
    return jsonify(error="not_found"), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify(error="method_not_allowed"), 405


@app.errorhandler(500)
def internal_error(e):
    app.logger.error(e)
    return jsonify(error="internal_server_error"), 500


@app.get("/books")
def list_books():
    DEFAULT_SIZE = 20
    MAX_SIZE = 100

    try:
        page = max(int(request.args.get("page", 1)), 1)
        size = int(request.args.get("size", DEFAULT_SIZE))
        size = max(min(size, MAX_SIZE), 1)
    except ValueError:
        return jsonify(error="page and size must be integers"), 400

    author = request.args.get("author")
    q = (request.args.get("q") or "").strip().lower()

    with get_db() as conn:
        sql = "SELECT * FROM books WHERE 1=1"
        params = []

        if author:
            sql += " AND LOWER(author) = LOWER(?)"
            params.append(author)
        if q:
            sql += " AND LOWER(title) LIKE ?"
            params.append(f"%{q}%")

        total = conn.execute(
            f"SELECT COUNT(*) FROM ({sql})", params
        ).fetchone()[0]

        offset = (page - 1) * size
        rows = conn.execute(
            sql + " LIMIT ? OFFSET ?", params + [size, offset]
        ).fetchall()

    items = [dict(r) for r in rows]
    total_pages = max((total + size - 1) // size, 1)

    links = {
        "self": {"href": f"/books?page={page}&size={size}"},
        "first": {"href": f"/books?page=1&size={size}"},
        "last": {"href": f"/books?page={total_pages}&size={size}"},
    }
    if page > 1:
        links["prev"] = {"href": f"/books?page={page - 1}&size={size}"}
    if page < total_pages:
        links["next"] = {"href": f"/books?page={page + 1}&size={size}"}

    body = {
        "data": items,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": total_pages,
        },
        "_links": links,
    }

    resp = make_response(jsonify(body), 200)
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp


@app.post("/books")
def create_book():
    if not request.is_json:
        return jsonify(error="Content-Type must be application/json"), 415

    p = request.get_json(silent=True) or {}
    title = (p.get("title") or "").strip()
    author = (p.get("author") or "").strip()

    if not title or not author:
        return jsonify(error="title and author are required"), 422

    isbn = p.get("isbn")
    price = p.get("price")

    if price is not None and price < 0:
        return jsonify(error="price must be non-negative"), 422

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, isbn, price) VALUES (?, ?, ?, ?)",
            (title, author, isbn, price),
        )
        book_id = cur.lastrowid
        book = dict(conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone())

    resp = make_response(jsonify(book), 201)
    resp.headers["Location"] = f"/books/{book_id}"
    return resp


@app.get("/books/<int:bid>")
def get_book(bid):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (bid,)
        ).fetchone()

    if not row:
        return jsonify(error="not_found"), 404

    resp = make_response(jsonify(dict(row)), 200)
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp


@app.put("/books/<int:bid>")
def put_book(bid):
    if not request.is_json:
        return jsonify(error="Content-Type must be application/json"), 415

    with get_db() as conn:
        row = conn.execute("SELECT id FROM books WHERE id = ?", (bid,)).fetchone()
        if not row:
            return jsonify(error="not_found"), 404

        p = request.get_json(silent=True) or {}
        title = (p.get("title") or "").strip()
        author = (p.get("author") or "").strip()

        if not title or not author:
            return jsonify(error="title and author are required"), 422

        price = p.get("price")
        if price is not None and price < 0:
            return jsonify(error="price must be non-negative"), 422

        conn.execute(
            "UPDATE books SET title=?, author=?, isbn=?, price=? WHERE id=?",
            (title, author, p.get("isbn"), price, bid),
        )
        book = dict(conn.execute(
            "SELECT * FROM books WHERE id = ?", (bid,)
        ).fetchone())

    return jsonify(book), 200


@app.patch("/books/<int:bid>")
def patch_book(bid):
    if not request.is_json:
        return jsonify(error="Content-Type must be application/json"), 415

    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
        if not row:
            return jsonify(error="not_found"), 404

        p = request.get_json(silent=True) or {}
        allowed = {"title", "author", "isbn", "price"}
        updates = {k: v for k, v in p.items() if k in allowed}

        if not updates:
            return jsonify(error="no valid fields to update"), 422

        if "price" in updates and updates["price"] is not None and updates["price"] < 0:
            return jsonify(error="price must be non-negative"), 422

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [bid]
        conn.execute(f"UPDATE books SET {set_clause} WHERE id = ?", values)

        book = dict(conn.execute(
            "SELECT * FROM books WHERE id = ?", (bid,)
        ).fetchone())

    return jsonify(book), 200


@app.delete("/books/<int:bid>")
def delete_book(bid):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM books WHERE id = ?", (bid,)).fetchone()
        if not row:
            return jsonify(error="not_found"), 404
        conn.execute("DELETE FROM books WHERE id = ?", (bid,))

    return "", 204


@app.get("/orders")
def list_orders():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM orders").fetchall()
    orders = [dict(r) for r in rows]
    return jsonify({"data": orders, "total": len(orders)}), 200


@app.post("/orders")
def create_order():
    if not request.is_json:
        return jsonify(error="Content-Type must be application/json"), 415

    p = request.get_json(silent=True) or {}
    book_id = p.get("book_id")
    quantity = p.get("quantity", 1)

    if not book_id:
        return jsonify(error="book_id is required"), 422
    if not isinstance(quantity, int) or quantity < 1:
        return jsonify(error="quantity must be a positive integer"), 422

    with get_db() as conn:
        book = conn.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
        if not book:
            return jsonify(error=f"book {book_id} not found"), 404

        cur = conn.execute(
            "INSERT INTO orders (book_id, quantity) VALUES (?, ?)",
            (book_id, quantity),
        )
        oid = cur.lastrowid
        order = dict(conn.execute(
            "SELECT * FROM orders WHERE id = ?", (oid,)
        ).fetchone())

    resp = make_response(jsonify(order), 201)
    resp.headers["Location"] = f"/orders/{oid}"
    return resp


@app.get("/orders/<int:oid>")
def get_order(oid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()

    if not row:
        return jsonify(error="not_found"), 404

    order = dict(row)
    order["_links"] = {
        "self": {"href": f"/orders/{oid}"},
        "book": {"href": f"/books/{order['book_id']}"},
    }
    if order["status"] == "pending":
        order["_links"]["cancel"] = {
            "href": f"/orders/{oid}/cancel",
            "method": "POST",
        }

    return jsonify(order), 200


@app.post("/orders/<int:oid>/cancel")
def cancel_order(oid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
        if not row:
            return jsonify(error="not_found"), 404
        if row["status"] != "pending":
            return jsonify(error=f"cannot cancel order with status '{row['status']}'"), 409

        conn.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (oid,))
        order = dict(conn.execute(
            "SELECT * FROM orders WHERE id = ?", (oid,)
        ).fetchone())

    return jsonify(order), 200


if __name__ == "__main__":
    app.run(debug=True)
