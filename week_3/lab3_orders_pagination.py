"""Lab 3: Orders API voi cursor pagination."""

import base64
import binascii
import json
import math
from datetime import datetime

from flask import Flask, jsonify, request


app = Flask(__name__)
app.json.sort_keys = False


ORDERS = [
    {
        "id": "ord-1001",
        "customer_id": "cus-001",
        "status": "paid",
        "total": 129.99,
        "currency": "USD",
        "created_at": "2026-10-01T08:10:00Z",
    },
    {
        "id": "ord-1002",
        "customer_id": "cus-002",
        "status": "pending",
        "total": 75.50,
        "currency": "USD",
        "created_at": "2026-10-01T09:35:00Z",
    },
    {
        "id": "ord-1003",
        "customer_id": "cus-001",
        "status": "shipped",
        "total": 240.00,
        "currency": "USD",
        "created_at": "2026-10-01T13:20:00Z",
    },
    {
        "id": "ord-1004",
        "customer_id": "cus-003",
        "status": "paid",
        "total": 19.99,
        "currency": "USD",
        "created_at": "2026-10-02T07:00:00Z",
    },
    {
        "id": "ord-1005",
        "customer_id": "cus-004",
        "status": "cancelled",
        "total": 310.25,
        "currency": "USD",
        "created_at": "2026-10-02T08:45:00Z",
    },
    {
        "id": "ord-1006",
        "customer_id": "cus-002",
        "status": "paid",
        "total": 48.00,
        "currency": "USD",
        "created_at": "2026-10-02T10:05:00Z",
    },
    {
        "id": "ord-1007",
        "customer_id": "cus-005",
        "status": "pending",
        "total": 599.90,
        "currency": "USD",
        "created_at": "2026-10-02T15:40:00Z",
    },
    {
        "id": "ord-1008",
        "customer_id": "cus-003",
        "status": "refunded",
        "total": 44.40,
        "currency": "USD",
        "created_at": "2026-10-03T06:25:00Z",
    },
    {
        "id": "ord-1009",
        "customer_id": "cus-001",
        "status": "paid",
        "total": 89.00,
        "currency": "USD",
        "created_at": "2026-10-03T11:50:00Z",
    },
    {
        "id": "ord-1010",
        "customer_id": "cus-006",
        "status": "shipped",
        "total": 150.75,
        "currency": "USD",
        "created_at": "2026-10-03T16:30:00Z",
    },
    {
        "id": "ord-1011",
        "customer_id": "cus-004",
        "status": "paid",
        "total": 220.20,
        "currency": "USD",
        "created_at": "2026-10-04T09:00:00Z",
    },
    {
        "id": "ord-1012",
        "customer_id": "cus-002",
        "status": "pending",
        "total": 35.00,
        "currency": "USD",
        "created_at": "2026-10-04T12:15:00Z",
    },
]

DEFAULT_LIMIT = 10
MAX_LIMIT = 100
DEFAULT_SORT = "-created_at"
ALLOWED_STATUSES = {"paid", "pending", "shipped", "cancelled", "refunded"}
ALLOWED_SORT_FIELDS = {"created_at", "id", "total", "status", "customer_id"}
ORDER_FIELDS = ("id", "customer_id", "status", "total", "currency", "created_at")


def error_response(status, code, message):
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status
    return response


def parse_limit():
    raw_limit = request.args.get("limit", str(DEFAULT_LIMIT))

    try:
        limit = int(raw_limit)
    except ValueError:
        return None, error_response(400, "invalid-limit", "limit must be an integer.")

    if limit < 1 or limit > MAX_LIMIT:
        return None, error_response(400, "invalid-limit", f"limit must be between 1 and {MAX_LIMIT}.")

    return limit, None


def parse_sort():
    raw_sort = request.args.get("sort", DEFAULT_SORT)
    direction = "desc" if raw_sort.startswith("-") else "asc"
    field = raw_sort[1:] if raw_sort.startswith("-") else raw_sort

    if not field or "," in raw_sort or field not in ALLOWED_SORT_FIELDS:
        allowed = ", ".join(sorted(ALLOWED_SORT_FIELDS))
        return None, None, error_response(400, "invalid-sort", f"sort must be one of: {allowed}.")

    return field, direction, None


def parse_fields():
    raw_fields = request.args.get("fields")
    if raw_fields is None:
        return list(ORDER_FIELDS), None

    fields = []
    for field in raw_fields.split(","):
        normalized_field = field.strip()
        if not normalized_field:
            return None, error_response(400, "invalid-fields", "fields cannot contain an empty name.")
        if normalized_field not in fields:
            fields.append(normalized_field)

    unknown_fields = sorted(set(fields) - set(ORDER_FIELDS))
    if unknown_fields:
        return None, error_response(400, "invalid-fields", f"Unknown fields: {', '.join(unknown_fields)}.")

    return fields, None


def encode_cursor(order, sort, filters):
    payload = {
        "id": order["id"],
        "value": order[sort.lstrip("-")],
        "sort": sort,
        "filters": filters,
    }
    raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw_json).decode("ascii").rstrip("=")


def decode_cursor(raw_cursor, sort, filters):
    if raw_cursor is None:
        return None, None

    try:
        if not raw_cursor or len(raw_cursor) > 4096:
            raise ValueError
        padded_cursor = raw_cursor + ("=" * (-len(raw_cursor) % 4))
        decoded = base64.b64decode(padded_cursor, altchars=b"-_", validate=True).decode("utf-8")
        payload = json.loads(decoded)
        if not isinstance(payload, dict) or set(payload) != {"id", "value", "sort", "filters"}:
            raise ValueError
        if not isinstance(payload["id"], str) or not payload["id"]:
            raise ValueError
        if payload["sort"] != sort or payload["filters"] != filters:
            raise ValueError

        field = sort.lstrip("-")
        value = payload["value"]
        if field == "total":
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError
        elif not isinstance(value, str) or not value:
            raise ValueError
        if field == "created_at":
            parsed_time = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            if parsed_time.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
                raise ValueError
        if field == "id" and value != payload["id"]:
            raise ValueError
    except (ValueError, binascii.Error, OverflowError, RecursionError):
        return None, error_response(400, "invalid-cursor", "cursor is invalid for the current sort and filters.")

    return payload, None


def filter_orders(orders, filters):
    filtered = orders

    status = filters["status"]
    if status is not None:
        if status not in ALLOWED_STATUSES:
            return None, error_response(400, "invalid-status", "status is not supported.")
        filtered = [order for order in filtered if order["status"] == status]

    customer_id = filters["customer_id"]
    if customer_id is not None:
        if not customer_id.strip():
            return None, error_response(400, "invalid-customer-id", "customer_id cannot be empty.")
        filtered = [order for order in filtered if order["customer_id"] == customer_id]

    return filtered, None


def sparse_order(order, fields):
    return {field: order[field] for field in fields}


@app.get("/orders")
@app.get("/api/v1/orders")
def list_orders():
    limit, error = parse_limit()
    if error:
        return error

    sort_field, sort_direction, error = parse_sort()
    if error:
        return error

    fields, error = parse_fields()
    if error:
        return error

    sort_param = request.args.get("sort", DEFAULT_SORT)
    filters = {
        "status": request.args.get("status"),
        "customer_id": request.args.get("customer_id"),
    }

    filtered_orders, error = filter_orders(ORDERS, filters)
    if error:
        return error

    cursor_payload, error = decode_cursor(request.args.get("cursor"), sort_param, filters)
    if error:
        return error

    reverse = sort_direction == "desc"
    sorted_orders = sorted(
        filtered_orders,
        key=lambda order: (order[sort_field], order["id"]),
        reverse=reverse,
    )

    if cursor_payload:
        # ID phan biet cac don co cung gia tri sort; moc van dung khi don bi xoa.
        boundary = (cursor_payload["value"], cursor_payload["id"])
        if reverse:
            sorted_orders = [order for order in sorted_orders if (order[sort_field], order["id"]) < boundary]
        else:
            sorted_orders = [order for order in sorted_orders if (order[sort_field], order["id"]) > boundary]

    page_items = sorted_orders[:limit]
    has_more = len(sorted_orders) > limit
    next_cursor = encode_cursor(page_items[-1], sort_param, filters) if has_more else None

    return jsonify(
        {
            "data": [sparse_order(order, fields) for order in page_items],
            "page": {
                "limit": limit,
                "count": len(page_items),
                "has_more": has_more,
                "next_cursor": next_cursor,
            },
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5003)
