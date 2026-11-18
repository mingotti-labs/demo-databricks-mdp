"""Helpers for the pattern-scd2-history-migration probes: SQL on a warehouse and a
scratch pipeline driven through the Databricks CLI."""

import json
import subprocess
import time

SCHEMA = "mdp_dev.pattern_bronze_publish"


def cli(profile: str, *args: str) -> dict:
    out = subprocess.run(
        ["databricks", *args, "--profile", profile, "-o", "json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out) if out.strip() else {}


def sql(profile: str, warehouse: str, statement: str) -> list[list]:
    body = {"warehouse_id": warehouse, "statement": statement, "wait_timeout": "50s"}
    out = cli(profile, "api", "post", "/api/2.0/sql/statements", "--json", json.dumps(body))
    while out["status"]["state"] in ("PENDING", "RUNNING"):
        out = cli(profile, "api", "get", f"/api/2.0/sql/statements/{out['statement_id']}")
    if out["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(out["status"])
    return out["result"].get("data_array") or []


def show(profile: str, warehouse: str, title: str, statement: str) -> list[list]:
    rows = sql(profile, warehouse, statement)
    print(f"--- {title}")
    for row in rows:
        print("  ", row)
    return rows


def upload(profile: str, local: str, remote: str) -> None:
    folder = remote.rsplit("/", 1)[0]
    cli(profile, "workspace", "mkdirs", folder)
    cli(profile, "workspace", "import", remote, "--file", local, "--format", "RAW", "--overwrite")


def create_pipeline(profile: str, name: str, paths: list[str]) -> str:
    spec = {
        "name": name,
        "catalog": "mdp_dev",
        "schema": "pattern_bronze_publish",
        "serverless": True,
        "continuous": False,
        "libraries": [{"file": {"path": p}} for p in paths],
    }
    return cli(profile, "pipelines", "create", "--json", json.dumps(spec))["pipeline_id"]


def run_update(profile: str, pipeline_id: str) -> str:
    update_id = cli(profile, "pipelines", "start-update", pipeline_id)["update_id"]
    while True:
        state = cli(profile, "pipelines", "get-update", pipeline_id, update_id)["update"]["state"]
        if state in ("COMPLETED", "FAILED", "CANCELED"):
            print(f"--- update {update_id}: {state}")
            if state != "COMPLETED":
                print_errors(profile, pipeline_id, update_id)
            return state
        time.sleep(15)


def print_errors(profile: str, pipeline_id: str, update_id: str) -> None:
    events = cli(profile, "pipelines", "list-pipeline-events", pipeline_id, "--max-results", "100")
    for e in events if isinstance(events, list) else events.get("events", []):
        if e.get("origin", {}).get("update_id") == update_id and e.get("level") == "ERROR":
            for ex in e.get("error", {}).get("exceptions", []):
                print("   ERROR:", ex.get("message", "")[:600])
