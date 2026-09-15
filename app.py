from uuid import uuid4
from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.sort_keys = False
STUDENTS = []
ORDERS = {
    "ord-1": {"id": "ord-1", "status": "pending"},
    "ord-2": {"id": "ord-2", "status": "shipped"},
}
BOOKS = [
    {"id": 1, "title": "Clean Code", "author": "R. Martin"},
    {"id": 2, "title": "The Pragmatic Programmer", "author": "A. Hunt"},
]
next_book_id = 3

@app.route("/", methods=["GET"])
def index():
    return {"message": "Hello, API!"}
@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200
@app.route("/echo", methods=["POST"])
def echo():
    data = request.get_json(silent=True) or {}
    return {"you_sent": data}, 200
@app.route("/students", methods=["POST"])
def create_student():
    body = request.get_json(silent=True) or {}
    name = body.get("name")

    if not name:
        return {"error": "name la bat buoc"}, 400

    student = {
        "id": str(uuid4()),
        "name": name,
        "gpa": body.get("gpa", 0.0),
    }
    STUDENTS.append(student)
    return student, 201, {"Location": f"/students/{student['id']}"}

@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    return {"id": item_id}, 200

@app.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return {"error": "not found"}, 404
    if order["status"] in ("shipped", "delivered"):
        return {"error": "cannot delete"}, 409

    ORDERS.pop(order_id)
    return "", 204
@app.route("/books", methods=["GET"])
def list_books():
    limit = int(request.args.get("limit", 100))
    q = request.args.get("q", "").strip().lower()

    res = [b for b in BOOKS if q in b["title"].lower()] if q else BOOKS
    return res[:limit], 200

@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    for book in BOOKS:
        if book["id"] == book_id:
            return book, 200
    return {"error": "not found"}, 404

@app.route("/books", methods=["POST"])
def create_book():
    global next_book_id

    body = request.get_json(silent=True) or {}
    title = body.get("title")
    author = body.get("author")

    if not title or not author:
        return {"error": "title and author are required"}, 400

    book = {
        "id": next_book_id,
        "title": title,
        "author": author,
    }
    next_book_id += 1
    BOOKS.append(book)
    return book, 201, {"Location": f"/books/{book['id']}"}

@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    for book in BOOKS:
        if book["id"] == book_id:
            body = request.get_json(silent=True) or {}
            book["title"] = body.get("title", book["title"])
            book["author"] = body.get("author", book["author"])
            return book, 200
    return {"error": "not found"}, 404

@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    for book in BOOKS:
        if book["id"] == book_id:
            BOOKS.remove(book)
            return "", 204
    return {"error": "not found"}, 404
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
