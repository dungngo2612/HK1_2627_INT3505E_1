"""Read final Locust HTML statistics, including requests after the last CSV tick."""

import csv
import json
from pathlib import Path


def load_final_stats(html_path):
    path = Path(html_path)
    text = path.read_text(encoding="utf-8")
    _, marker, payload = text.partition("window.templateArgs = ")
    if not marker:
        raise RuntimeError(f"Missing Locust report data: {path}")
    report = json.JSONDecoder().raw_decode(payload.lstrip())[0]
    if report["exceptions_statistics"]:
        raise RuntimeError(f"Locust task exceptions in {path}")
    percentiles = {
        (row["method"], row["name"]): row for row in report["response_time_statistics"]
    }
    rows = []
    for row in report["requests_statistics"]:
        pct = percentiles[(row["method"], row["name"])]
        rows.append({
            "Type": row["method"], "Name": row["name"],
            "Request Count": row["num_requests"], "Failure Count": row["num_failures"],
            "Average Response Time": row["avg_response_time"],
            "Min Response Time": row["min_response_time"],
            "Max Response Time": row["max_response_time"],
            "Requests/s": row["total_rps"], "50%": pct["0.5"],
            "95%": pct["0.95"], "99%": pct["0.99"],
        })
    if not rows:
        raise RuntimeError(f"No request statistics in {path}")
    path.with_name(path.stem + "_final.json").write_text(json.dumps(report, indent=2) + "\n")
    with path.with_name(path.stem + "_final_stats.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return report, rows


def final_failures(report):
    return [{
        "Method": row["method"], "Name": row["name"],
        "Error": row["error"], "Occurrences": row["occurrences"],
    } for row in report["failures_statistics"]]
