"""Seed an isolated database, serve week 7, and collect real Locust reports."""

import argparse
import csv
import json
import os
from pathlib import Path
import platform
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from importlib.metadata import version
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
from zoneinfo import ZoneInfo


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from locust_report import load_final_stats

WEEK7 = HERE.parents[1] / "week7"
SCENARIOS = {
    "A": {"users": 10, "spawn_rate": 2, "seconds": 30},
    "B": {"users": 50, "spawn_rate": 5, "seconds": 60},
    "C": {"users": 200, "spawn_rate": 50, "seconds": 30},
}
OPENER = build_opener(ProxyHandler({}))


def wait_for_server(server, host):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError("Gunicorn exited; inspect server.log")
        try:
            with OPENER.open(f"{host}/api/v1/products?page=1&size=20", timeout=1) as response:
                body = json.load(response)
                if body.get("total") == 1000 and len(body.get("items", [])) == 20:
                    return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(0.1)
    raise RuntimeError("API was not ready after 30 seconds; inspect server.log")


def seed_database(environment):
    # Only the unique database inside this report directory is ever initialized.
    code = """
from product_api import create_app
from product_api.extensions import db
from bai1_product_api.models import Product
from sqlalchemy import insert
app = create_app()
with app.app_context():
    db.session.execute(insert(Product), [
        dict(sku=f'LOAD-{i:05d}', name=f'San pham thu nghiem {i:05d}',
             description='Du lieu rieng phuc vu load test. ' * 4,
             price_cents=10000 + i, qty_in_stock=100, archived=False)
        for i in range(1, 1001)
    ])
    db.session.commit()
"""
    subprocess.run(
        [sys.executable, "-m", "flask", "--app", "product_api:create_app", "db", "upgrade"],
        cwd=WEEK7, env=environment, check=True,
    )
    subprocess.run([sys.executable, "-c", code], cwd=WEEK7, env=environment, check=True)


def run_locust(directory, label, settings, host):
    command = [
        sys.executable, "-m", "locust", "-f", str(HERE / "locustfile.py"),
        "--host", host, "--headless", "--users", str(settings["users"]),
        "--spawn-rate", str(settings["spawn_rate"]),
        "--run-time", f"{settings['seconds']}s", "--stop-timeout", "5",
        "--html", str(directory / f"{label}.html"),
        "--csv", str(directory / label), "--csv-full-history", "--only-summary",
    ]
    print(f"Running {label}: {settings}", flush=True)
    started = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat()
    with (directory / f"{label}.log").open("w") as log:
        result = subprocess.run(
            command, cwd=HERE, stdout=log, stderr=subprocess.STDOUT,
            timeout=settings["seconds"] + 45,
        )
    (directory / f"{label}_command.json").write_text(json.dumps({
        "started_at": started, "command": command, "exit_code": result.returncode,
    }, ensure_ascii=False, indent=2) + "\n")
    if result.returncode not in (0, 1):
        raise RuntimeError(f"Locust {label} failed to run; inspect {label}.log")
    _report, entries = load_final_stats(directory / f"{label}.html")
    row = next(row for row in entries if row["Name"] == "Aggregated")
    count, failures = int(row["Request Count"]), int(row["Failure Count"])
    if count == 0:
        raise RuntimeError(f"Locust {label} recorded no requests")
    p95 = float(row["95%"])
    failure_rate = failures / count
    return {
        "scenario": label, **settings, "requests": count, "failures": failures,
        "failure_rate_percent": round(failure_rate * 100, 4),
        "p50_ms": float(row["50%"]), "p95_ms": p95,
        "p99_ms": float(row["99%"]), "max_ms": float(row["Max Response Time"]),
        "rps": round(float(row["Requests/s"]), 3),
        "slo_pass": count >= 100 and p95 < 300 and failure_rate < 0.01,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["all", *SCENARIOS], default="all")
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    directory = HERE / "reports" / now.strftime("%Y%m%d-%H%M%S-%f")
    directory.mkdir(parents=True)
    environment = os.environ.copy()
    # Keep existing developer APP_* and DB_URL settings out of the benchmark.
    for key in list(environment):
        if key.startswith("APP_"):
            del environment[key]
    environment.update({
        "DB_URL": f"sqlite:///{directory / 'benchmark.db'}",
        "INSTANCE_PATH": str(directory / "instance"), "LOG_LEVEL": "WARNING",
        "FLASK_SKIP_DOTENV": "1",
    })
    seed_database(environment)
    # Reserve a local ephemeral listening socket and pass it directly to Gunicorn.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    host = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server_command = [
        sys.executable, "-m", "gunicorn", "product_api:create_app()",
        "--bind", f"fd://{listener.fileno()}", "--workers", "2",
        "--worker-class", "sync", "--log-level", "warning",
    ]
    metadata = {
        "measured_at": now.isoformat(), "host": host,
        "endpoint": "GET /api/v1/products?page=1..50&size=20",
        "python": sys.version, "platform": platform.platform(),
        "machine": platform.machine(), "logical_cpus": os.cpu_count(),
        "sqlite": sqlite3.sqlite_version,
        "versions": {name: version(name) for name in [
            "locust", "Flask", "gunicorn", "SQLAlchemy", "Flask-SQLAlchemy",
        ]},
        "database": "Isolated SQLite file; 1000 active products; seeded through real migrations",
        "server_command": server_command,
        "wait_time_seconds": [1, 3], "request_timeout_seconds": 5,
        "warmup_seconds": 10, "minimum_requests": 100,
        "slo": "p95 < 300 ms AND failure rate < 1%",
        "summary_source": "Final Locust HTML; periodic *_stats.csv can omit the last requests",
        "limitations": [
            "API and load generator share the same machine",
            "Short runs including ramp-up; one run per scenario",
            "Local SQLite, without reverse proxy, TLS, authentication or internet latency",
            "Locust percentiles use rounded response-time histogram buckets",
        ],
    }
    (directory / "environment.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    summaries = []
    with (directory / "server.log").open("w") as log:
        server = None
        try:
            server = subprocess.Popen(
                server_command, cwd=WEEK7, env=environment, pass_fds=(listener.fileno(),),
                stdout=log, stderr=subprocess.STDOUT,
            )
            listener.close()
            wait_for_server(server, host)
            warmup = directory / "warmup"
            warmup.mkdir()
            result = run_locust(warmup, "warmup", {"users": 10, "spawn_rate": 5, "seconds": 10}, host)
            if result["failures"]:
                raise RuntimeError("Warmup requests failed; inspect warmup reports")
            selected = SCENARIOS if args.scenario == "all" else {args.scenario: SCENARIOS[args.scenario]}
            for label, settings in selected.items():
                summary = run_locust(directory, label, settings, host)
                summaries.append(summary)
                print(json.dumps(summary, ensure_ascii=False), flush=True)
        finally:
            listener.close()
            if server is not None:
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
            if summaries:
                (directory / "summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n")
                with (directory / "summary.csv").open("w", newline="") as output:
                    writer = csv.DictWriter(output, fieldnames=list(summaries[0]))
                    writer.writeheader()
                    writer.writerows(summaries)
    print(f"Reports: {directory}", flush=True)
    return 0 if summaries and all(row["slo_pass"] for row in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
