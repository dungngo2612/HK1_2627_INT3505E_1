# bai3.py - conditional request cho route xem chi tiet sach

import hashlib
import json
from flask import request, jsonify, make_response
from app import app, get_db


def build_etag(book):
    payload = json.dumps(book, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(payload.encode()).hexdigest()


@app.endpoint("get_book")
def get_book_with_cache(bid):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (bid,)
        ).fetchone()

    if not row:
        return jsonify(error="not_found"), 404

    book = dict(row)
    etag = build_etag(book)

    if request.headers.get("If-None-Match") == etag:
        return "", 304

    resp = make_response(jsonify(book), 200)
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp


if __name__ == "__main__":
    app.run(debug=True)
