"""Lab 1: Blog API."""

from datetime import datetime, timezone
from itertools import count

from flask import Flask, jsonify, request


app = Flask(__name__)
app.json.sort_keys = False


POSTS = [
    {
        "id": 1,
        "title": "API Design Principles",
        "slug": "api-design-principles",
        "content": "Use nouns for resources, HTTP methods for actions.",
        "author_id": 1,
        "tag_ids": [1, 2],
        "status": "published",
        "created_at": "2026-10-01T09:00:00Z",
        "updated_at": "2026-10-01T09:00:00Z",
    },
    {
        "id": 2,
        "title": "RESTful Routing Checklist",
        "slug": "restful-routing-checklist",
        "content": "Keep paths predictable and version public APIs.",
        "author_id": 2,
        "tag_ids": [1, 3],
        "status": "draft",
        "created_at": "2026-10-02T10:30:00Z",
        "updated_at": "2026-10-02T10:30:00Z",
    },
]

COMMENTS = [
    {
        "id": 1,
        "post_id": 1,
        "author_id": 2,
        "content": "Clear and easy to follow.",
        "created_at": "2026-10-01T10:00:00Z",
    },
    {
        "id": 2,
        "post_id": 1,
        "author_id": 3,
        "content": "The route naming examples are useful.",
        "created_at": "2026-10-01T11:15:00Z",
    },
]

TAGS = [
    {"id": 1, "name": "api", "slug": "api"},
    {"id": 2, "name": "rest", "slug": "rest"},
    {"id": 3, "name": "best-practices", "slug": "best-practices"},
]

USERS = [
    {
        "id": 1,
        "username": "alice",
        "display_name": "Alice Nguyen",
        "following": [2],
        "followers": [],
    },
    {
        "id": 2,
        "username": "binh",
        "display_name": "Binh Tran",
        "following": [],
        "followers": [1],
    },
    {
        "id": 3,
        "username": "chi",
        "display_name": "Chi Le",
        "following": [],
        "followers": [],
    },
]

VALID_POST_STATUSES = {"draft", "published", "archived"}
DEFAULT_USER_ID = 1
POST_IDS = count(max(post["id"] for post in POSTS) + 1)
COMMENT_IDS = count(max(comment["id"] for comment in COMMENTS) + 1)


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def find_by_id(items, item_id):
    return next((item for item in items if item["id"] == item_id), None)


def error_response(status, code, message):
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status
    return response


def read_json_object():
    if not request.is_json:
        return None, error_response(415, "unsupported-media-type", "Content-Type must be application/json.")

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, error_response(400, "invalid-json", "Request body must be a JSON object.")

    return payload, None


def parse_positive_int(value, field_name):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, error_response(400, "invalid-query-parameter", f"{field_name} must be an integer.")

    if parsed <= 0:
        return None, error_response(400, "invalid-query-parameter", f"{field_name} must be positive.")

    return parsed, None


def normalize_tag_ids(raw_tag_ids):
    if not isinstance(raw_tag_ids, list):
        return None, error_response(422, "invalid-field", "tag_ids must be a list of tag IDs.")

    tag_ids = []
    known_tag_ids = {tag["id"] for tag in TAGS}

    for raw_tag_id in raw_tag_ids:
        if type(raw_tag_id) is not int:
            return None, error_response(422, "invalid-field", "Each tag ID must be an integer.")
        if raw_tag_id not in known_tag_ids:
            return None, error_response(422, "unknown-tag", f"Tag {raw_tag_id} does not exist.")
        if raw_tag_id not in tag_ids:
            tag_ids.append(raw_tag_id)

    return tag_ids, None


def serialize_post(post):
    tags = [tag for tag in TAGS if tag["id"] in post["tag_ids"]]
    author = find_by_id(USERS, post["author_id"])

    return {
        "id": post["id"],
        "title": post["title"],
        "slug": post["slug"],
        "content": post["content"],
        "status": post["status"],
        "author": {
            "id": author["id"],
            "username": author["username"],
            "display_name": author["display_name"],
        }
        if author
        else None,
        "tags": tags,
        "created_at": post["created_at"],
        "updated_at": post["updated_at"],
    }


def serialize_comment(comment):
    author = find_by_id(USERS, comment["author_id"])

    return {
        "id": comment["id"],
        "post_id": comment["post_id"],
        "content": comment["content"],
        "author": {
            "id": author["id"],
            "username": author["username"],
            "display_name": author["display_name"],
        }
        if author
        else None,
        "created_at": comment["created_at"],
    }


def serialize_user(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "follower_count": len(user["followers"]),
        "following_count": len(user["following"]),
    }


def current_user():
    # X-User-Id chi mo phong nguoi dung cho bai lab, khong phai xac thuc.
    raw_user_id = request.headers.get("X-User-Id")
    if raw_user_id is None:
        user_id = DEFAULT_USER_ID
    else:
        user_id, error = parse_positive_int(raw_user_id, "X-User-Id")
        if error:
            return None, error

    user = find_by_id(USERS, user_id)
    if user is None:
        return None, error_response(400, "unknown-user", "X-User-Id must reference an existing user.")

    return user, None


@app.get("/api/v1/posts")
def list_posts():
    posts = POSTS

    status = request.args.get("status")
    if status:
        if status not in VALID_POST_STATUSES:
            return error_response(400, "invalid-status", "status must be draft, published, or archived.")
        posts = [post for post in posts if post["status"] == status]

    author_id = request.args.get("author_id")
    if author_id:
        parsed_author_id, error = parse_positive_int(author_id, "author_id")
        if error:
            return error
        posts = [post for post in posts if post["author_id"] == parsed_author_id]

    tag_slug = request.args.get("tag")
    if tag_slug:
        tag = next((item for item in TAGS if item["slug"] == tag_slug), None)
        posts = [post for post in posts if tag and tag["id"] in post["tag_ids"]]

    return jsonify({"data": [serialize_post(post) for post in posts], "count": len(posts)})


@app.post("/api/v1/posts")
def create_post():
    payload, error = read_json_object()
    if error:
        return error

    title = payload.get("title")
    content = payload.get("content")
    author_id = payload.get("author_id")
    status = payload.get("status", "draft")

    if not isinstance(title, str) or not title.strip():
        return error_response(422, "invalid-title", "title must be a non-empty string.")
    if not isinstance(content, str) or not content.strip():
        return error_response(422, "invalid-content", "content must be a non-empty string.")
    if type(author_id) is not int or find_by_id(USERS, author_id) is None:
        return error_response(422, "unknown-author", "author_id must reference an existing user.")
    if not isinstance(status, str) or status not in VALID_POST_STATUSES:
        return error_response(422, "invalid-status", "status must be draft, published, or archived.")

    tag_ids, error = normalize_tag_ids(payload.get("tag_ids", []))
    if error:
        return error

    now = utc_now()
    title = title.strip()
    post = {
        "id": next(POST_IDS),
        "title": title,
        "slug": "-".join(title.lower().split()),
        "content": content.strip(),
        "author_id": author_id,
        "tag_ids": tag_ids,
        "status": status,
        "created_at": now,
        "updated_at": now,
    }
    POSTS.append(post)

    response = jsonify({"data": serialize_post(post)})
    response.status_code = 201
    response.headers["Location"] = f"/api/v1/posts/{post['id']}"
    return response


@app.get("/api/v1/posts/<int:post_id>")
def get_post(post_id):
    post = find_by_id(POSTS, post_id)
    if post is None:
        return error_response(404, "post-not-found", f"Post {post_id} was not found.")

    return jsonify({"data": serialize_post(post)})


@app.patch("/api/v1/posts/<int:post_id>")
def update_post(post_id):
    post = find_by_id(POSTS, post_id)
    if post is None:
        return error_response(404, "post-not-found", f"Post {post_id} was not found.")

    payload, error = read_json_object()
    if error:
        return error

    allowed_fields = {"title", "content", "status", "tag_ids"}
    if not payload or set(payload) - allowed_fields:
        return error_response(422, "invalid-fields", "Provide title, content, status, or tag_ids.")

    changes = {}
    if "title" in payload:
        title = payload["title"]
        if not isinstance(title, str) or not title.strip():
            return error_response(422, "invalid-title", "title must be a non-empty string.")
        changes["title"] = title.strip()
        changes["slug"] = "-".join(title.lower().split())

    if "content" in payload:
        content = payload["content"]
        if not isinstance(content, str) or not content.strip():
            return error_response(422, "invalid-content", "content must be a non-empty string.")
        changes["content"] = content.strip()

    if "status" in payload:
        status = payload["status"]
        if not isinstance(status, str) or status not in VALID_POST_STATUSES:
            return error_response(422, "invalid-status", "status must be draft, published, or archived.")
        changes["status"] = status

    if "tag_ids" in payload:
        tag_ids, error = normalize_tag_ids(payload["tag_ids"])
        if error:
            return error
        changes["tag_ids"] = tag_ids

    # Chi cap nhat sau khi tat ca cac truong da hop le.
    changes["updated_at"] = utc_now()
    post.update(changes)
    return jsonify({"data": serialize_post(post)})


@app.delete("/api/v1/posts/<int:post_id>")
def delete_post(post_id):
    post = find_by_id(POSTS, post_id)
    if post is None:
        return error_response(404, "post-not-found", f"Post {post_id} was not found.")

    POSTS.remove(post)
    COMMENTS[:] = [comment for comment in COMMENTS if comment["post_id"] != post_id]
    return "", 204


@app.get("/api/v1/posts/<int:post_id>/comments")
def list_post_comments(post_id):
    if find_by_id(POSTS, post_id) is None:
        return error_response(404, "post-not-found", f"Post {post_id} was not found.")

    comments = [comment for comment in COMMENTS if comment["post_id"] == post_id]
    return jsonify({"data": [serialize_comment(comment) for comment in comments], "count": len(comments)})


@app.post("/api/v1/posts/<int:post_id>/comments")
def create_post_comment(post_id):
    if find_by_id(POSTS, post_id) is None:
        return error_response(404, "post-not-found", f"Post {post_id} was not found.")

    payload, error = read_json_object()
    if error:
        return error

    content = payload.get("content")
    author_id = payload.get("author_id")

    if not isinstance(content, str) or not content.strip():
        return error_response(422, "invalid-content", "content must be a non-empty string.")
    if type(author_id) is not int or find_by_id(USERS, author_id) is None:
        return error_response(422, "unknown-author", "author_id must reference an existing user.")

    comment = {
        "id": next(COMMENT_IDS),
        "post_id": post_id,
        "author_id": author_id,
        "content": content.strip(),
        "created_at": utc_now(),
    }
    COMMENTS.append(comment)

    response = jsonify({"data": serialize_comment(comment)})
    response.status_code = 201
    response.headers["Location"] = f"/api/v1/posts/{post_id}/comments/{comment['id']}"
    return response


@app.get("/api/v1/posts/<int:post_id>/comments/<int:comment_id>")
def get_post_comment(post_id, comment_id):
    comment = find_by_id(COMMENTS, comment_id)
    if comment is None or comment["post_id"] != post_id:
        return error_response(404, "comment-not-found", f"Comment {comment_id} was not found.")
    return jsonify({"data": serialize_comment(comment)})


@app.get("/api/v1/tags")
def list_tags():
    data = []
    for tag in TAGS:
        data.append(
            {
                "id": tag["id"],
                "name": tag["name"],
                "slug": tag["slug"],
                "post_count": sum(1 for post in POSTS if tag["id"] in post["tag_ids"]),
            }
        )

    return jsonify({"data": data, "count": len(data)})


@app.get("/api/v1/users")
def list_users():
    return jsonify({"data": [serialize_user(user) for user in USERS], "count": len(USERS)})


@app.get("/api/v1/users/<int:user_id>")
def get_user(user_id):
    user = find_by_id(USERS, user_id)
    if user is None:
        return error_response(404, "user-not-found", f"User {user_id} was not found.")

    return jsonify({"data": serialize_user(user)})


@app.post("/api/v1/users/<int:user_id>/follow")
def follow_user(user_id):
    target_user = find_by_id(USERS, user_id)
    if target_user is None:
        return error_response(404, "user-not-found", f"User {user_id} was not found.")

    actor, error = current_user()
    if error:
        return error

    if actor["id"] == target_user["id"]:
        return error_response(409, "cannot-follow-self", "Users cannot follow themselves.")

    if target_user["id"] not in actor["following"]:
        actor["following"].append(target_user["id"])
    if actor["id"] not in target_user["followers"]:
        target_user["followers"].append(actor["id"])

    return jsonify(
        {
            "data": {
                "follower_id": actor["id"],
                "followed_user_id": target_user["id"],
                "status": "following",
            }
        }
    )


@app.delete("/api/v1/users/<int:user_id>/follow")
def unfollow_user(user_id):
    target_user = find_by_id(USERS, user_id)
    if target_user is None:
        return error_response(404, "user-not-found", f"User {user_id} was not found.")

    actor, error = current_user()
    if error:
        return error

    if target_user["id"] in actor["following"]:
        actor["following"].remove(target_user["id"])
    if actor["id"] in target_user["followers"]:
        target_user["followers"].remove(actor["id"])

    return "", 204


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)
