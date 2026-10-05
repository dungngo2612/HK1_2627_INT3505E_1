"""Lab 2: Error handler voi application/problem+json."""

from http import HTTPStatus
from uuid import uuid4

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


app = Flask(__name__)
app.json.sort_keys = False

PROBLEM_BASE_URL = "https://api.example.test/problems"

RESOURCES = {
    "1": {"id": "1", "name": "SOA lecture note", "kind": "document"},
    "2": {"id": "2", "name": "API design checklist", "kind": "checklist"},
}


class ApiProblem(Exception):
    def __init__(self, status, title, detail, type_path="about:blank", **extra):
        super().__init__(detail)
        self.status = int(status)
        self.title = title
        self.detail = detail
        self.type_path = type_path
        self.extra = extra


def problem_type(type_path):
    if type_path.startswith("http://") or type_path.startswith("https://") or type_path == "about:blank":
        return type_path
    return f"{PROBLEM_BASE_URL}/{type_path.strip('/')}"


def build_problem_response(problem, response=None):
    trace_id = str(uuid4())
    body = {
        "type": problem_type(problem.type_path),
        "title": problem.title,
        "status": problem.status,
        "detail": problem.detail,
        "instance": request.path,
        "trace_id": trace_id,
    }

    reserved_fields = set(body)
    for key, value in problem.extra.items():
        if key not in reserved_fields:
            body[key] = value

    if response is None:
        response = jsonify(body)
    else:
        response.set_data(app.json.dumps(body))
    response.status_code = problem.status
    response.mimetype = "application/problem+json"
    return response


@app.errorhandler(ApiProblem)
def handle_api_problem(error):
    return build_problem_response(error)


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    status = error.code or 500
    if status >= 500:
        return handle_unexpected_exception(error, error.get_response())
    title = error.name or HTTPStatus(status).phrase
    detail = error.description or HTTPStatus(status).description

    return build_problem_response(
        ApiProblem(
            status=status,
            title=title,
            detail=detail,
            type_path=title.lower().replace(" ", "-"),
        ),
        response=error.get_response(),
    )


@app.errorhandler(Exception)
def handle_unexpected_exception(error, response=None):
    status = error.code if isinstance(error, HTTPException) and error.code else 500
    title = HTTPStatus(status).phrase
    response = build_problem_response(
        ApiProblem(
            status=status,
            title=title,
            detail="An unexpected error occurred.",
            type_path=title.lower().replace(" ", "-"),
        ),
        response=response,
    )
    app.logger.error(
        "Unhandled exception; trace_id=%s",
        response.get_json()["trace_id"],
        exc_info=(type(error), error, error.__traceback__),
    )
    return response


@app.get("/resources/<resource_id>")
def get_resource(resource_id):
    resource = RESOURCES.get(resource_id)
    if resource is None:
        raise ApiProblem(
            status=404,
            title="Resource Not Found",
            detail=f"Resource {resource_id} does not exist.",
            type_path="resource-not-found",
            resource_id=resource_id,
        )

    return jsonify({"data": resource})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002)
