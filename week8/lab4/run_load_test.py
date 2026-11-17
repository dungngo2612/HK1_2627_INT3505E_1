"""Run the three slide-30 scenarios and an optional connection-pool bonus."""

import argparse
import csv
from datetime import datetime
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
from zoneinfo import ZoneInfo


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from locust_report import final_failures, load_final_stats

OPENER = build_opener(ProxyHandler({}))
SCENARIOS = {
    "A": {"users": 10, "spawn_rate": 2, "seconds": 30},
    "B": {"users": 50, "spawn_rate": 5, "seconds": 60},
    "C": {"users": 200, "spawn_rate": 50, "seconds": 30},
}


def read_json(url):
    with OPENER.open(url, timeout=2) as response:
        return json.load(response)


def prepare_database(environment):
    script = """
from benchmark_app import create_app
from models import db, Book
from sqlalchemy import insert
app = create_app()
with app.app_context():
    db.session.execute(insert(Book), [
        dict(title=f'Seed book {i:04d}', author=f'Author {i % 10}',
             year=2000 + (i % 25), isbn=str(9780000000000 + i))
        for i in range(1, 1001)
    ])
    db.session.commit()
"""
    subprocess.run([sys.executable, "-c", script], cwd=HERE, env=environment, check=True)


def summarize(directory, label, settings, exit_code):
    report, entries = load_final_stats(directory / f"{label}.html")
    failures = final_failures(report)

    def metrics(row):
        count, failed = int(row["Request Count"]), int(row["Failure Count"])
        return {
            "name": row["Name"], "requests": count, "failures": failed,
            "failure_rate_percent": round(100 * failed / count, 4) if count else 0,
            "rps": round(float(row["Requests/s"]), 3),
            "p50_ms": float(row["50%"]), "p95_ms": float(row["95%"]),
            "p99_ms": float(row["99%"]),
        }

    total = metrics(next(row for row in entries if row["Name"] == "Aggregated"))
    if total["requests"] == 0:
        raise RuntimeError(f"Scenario {label} recorded no requests")
    return {
        "scenario": label, **settings, **total,
        "locust_exit_code": exit_code,
        "latency_slo_pass": total["p95_ms"] < 300,
        "gate_pass": total["requests"] >= 100 and total["p95_ms"] < 300
                     and total["failure_rate_percent"] < 1,
        "endpoints": [metrics(row) for row in entries if row["Name"] != "Aggregated"],
        "failures_by_message": failures,
    }


def run_scenario(directory, label, settings, failure_rate=0.01, pool_size=5, bonus=False):
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith("LAB4_"):
            del environment[key]
    environment.update({
        "LAB4_DB_PATH": str(directory / f"{label}.db"),
        "LAB4_FAILURE_RATE": str(failure_rate), "LAB4_POOL_SIZE": str(pool_size),
        "LAB4_POOL_TIMEOUT": "1",
        "LAB4_HOLD_MS": "100" if bonus else "0",
    })
    prepare_database(environment)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    host = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server_command = [
        sys.executable, "-m", "gunicorn", "benchmark_app:create_app()",
        "--bind", f"fd://{listener.fileno()}", "--workers", "1" if bonus else "2",
        "--worker-class", "gthread" if bonus else "sync", "--log-level", "warning",
    ]
    if bonus:
        server_command.extend(["--threads", "50"])
    command = [
        sys.executable, "-m", "locust", "-f", str(HERE / "locustfile.py"),
        "--host", host, "--headless", "--users", str(settings["users"]),
        "--spawn-rate", str(settings["spawn_rate"]), "--run-time", f"{settings['seconds']}s",
        "--stop-timeout", "5", "--html", str(directory / f"{label}.html"),
        "--csv", str(directory / label), "--csv-full-history", "--only-summary",
        "PoolSearchUser" if bonus else "BooksUser",
    ]
    configuration = {
        "started_at": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
        "host": host, "server_command": server_command, "locust_command": command,
        "failure_probability_per_search": failure_rate, "pool_size_per_worker": pool_size,
        "max_overflow": 0, "hold_ms": 100 if bonus else 0,
        "pool_timeout_seconds": 1,
        "seed_books": 1000, "warmup": "10 GET /books requests outside Locust statistics",
        **settings,
    }
    (directory / f"{label}_configuration.json").write_text(json.dumps(configuration, indent=2) + "\n")
    print(f"Running {label}: {settings}, pool={pool_size}, injected={failure_rate}", flush=True)
    server = None
    with (directory / f"{label}_server.log").open("w") as server_log:
        try:
            server = subprocess.Popen(
                server_command, cwd=HERE, env=environment, pass_fds=(listener.fileno(),),
                stdout=server_log, stderr=subprocess.STDOUT,
            )
            listener.close()
            deadline = time.monotonic() + 30
            while True:
                if server.poll() is not None:
                    raise RuntimeError(f"Server exited; inspect {label}_server.log")
                try:
                    if read_json(f"{host}/health")["status"] == "ok":
                        break
                except (URLError, OSError, TimeoutError):
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Server not ready; inspect {label}_server.log")
                time.sleep(0.1)
            for _ in range(10):
                assert len(read_json(f"{host}/books")) == 20
            with (directory / f"{label}.log").open("w") as log:
                result = subprocess.run(
                    command, cwd=HERE, stdout=log, stderr=subprocess.STDOUT,
                    timeout=settings["seconds"] + 45,
                )
            if result.returncode not in (0, 1):
                raise RuntimeError(f"Locust failed to run; inspect {label}.log")
            if server.poll() is not None:
                raise RuntimeError(f"Server stopped during scenario {label}")
            summary = summarize(directory, label, settings, result.returncode)
            if bonus:
                pool_metrics = read_json(f"{host}/lab/metrics")
                (directory / f"{label}_pool_metrics.json").write_text(json.dumps(pool_metrics, indent=2) + "\n")
                summary["pool_metrics"] = pool_metrics
            print(json.dumps(summary, ensure_ascii=False), flush=True)
            return summary
        finally:
            listener.close()
            if server is not None:
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["all", *SCENARIOS], default="all")
    parser.add_argument("--bonus", action="store_true", help="Compare pools of 5 and 20 real connections")
    parser.add_argument("--ci", action="store_true", help="Disable injected errors and enforce the SLO gate")
    args = parser.parse_args()
    if args.ci and args.bonus:
        parser.error("Run the pool experiment separately from the CI gate")
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    directory = HERE / "reports" / now.strftime("%Y%m%d-%H%M%S-%f")
    directory.mkdir(parents=True)
    metadata = {
        "started_at": now.isoformat(), "platform": platform.platform(),
        "python": sys.version, "logical_cpus": os.cpu_count(),
        "versions": {name: version(name) for name in ("locust", "Flask", "SQLAlchemy", "gunicorn")},
        "starter": json.loads((HERE / "starter_source.json").read_text()),
        "task_weights": {"list": 3, "read": 2, "create": 1, "search_by_year": 1},
        "wait_time_seconds": [1, 3], "request_timeout_seconds": 5,
        "ci_mode": args.ci,
        "summary_source": "Final Locust HTML; periodic *_stats.csv can omit the last requests",
    }
    (directory / "environment.json").write_text(json.dumps(metadata, indent=2) + "\n")
    labels = SCENARIOS if args.scenario == "all" else {args.scenario: SCENARIOS[args.scenario]}
    if args.ci and args.scenario == "all":
        labels = {"A": SCENARIOS["A"]}
    summaries = []
    for label, settings in labels.items():
        summaries.append(run_scenario(directory, label, settings, failure_rate=0 if args.ci else 0.01))
        (directory / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    if args.bonus:
        for size in (5, 20):
            summaries.append(run_scenario(
                directory, f"pool{size}", {"users": 200, "spawn_rate": 50, "seconds": 20},
                failure_rate=0, pool_size=size, bonus=True,
            ))
            (directory / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    fields = ["scenario", "users", "spawn_rate", "seconds", "requests", "failures",
              "failure_rate_percent", "rps", "p50_ms", "p95_ms", "p99_ms", "latency_slo_pass", "gate_pass"]
    with (directory / "summary.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summaries)
    # A partial/CI run preserves the complete assignment's analysis.
    if set(labels) == {"A", "B", "C"} and not args.ci:
        from analyze import write_analysis
        write_analysis(directory)
    print(f"Reports: {directory}", flush=True)
    return int(args.ci and not all(row["gate_pass"] for row in summaries))


if __name__ == "__main__":
    raise SystemExit(main())
