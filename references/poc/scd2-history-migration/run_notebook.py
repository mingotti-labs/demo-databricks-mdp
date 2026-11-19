"""Run a pattern notebook in dev as a one-time serverless job and print its cell outputs.

Usage: uv run python run_notebook.py --profile <PROFILE> --notebook <path.py> [--teardown]
"""

import argparse
import base64
import json
import re
import time
import urllib.parse
from pathlib import Path

from probe import cli


def outputs(profile: str, task_run_id: str) -> None:
    """Print the text and table outputs of a finished notebook task run."""
    for view in cli(profile, "jobs", "export-run", task_run_id, "--views-to-export", "CODE").get("views", []):
        m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", view.get("content", ""))
        if not m:
            continue
        model = json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode()))
        for cmd in model.get("commands", []):
            data = (cmd.get("results") or {}).get("data")
            if not isinstance(data, list) or not data:
                continue
            print("=== cell:", cmd.get("command", "").strip().splitlines()[0][:80])
            for o in data:
                if o.get("type") == "ansi":
                    print(o["data"].rstrip())
                elif o.get("type") == "table":
                    print(" | ".join(c["name"] for c in o.get("schema", [])))
                    for row in o["data"]:
                        print(" | ".join(str(x) for x in row))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--notebook", required=True)
    parser.add_argument("--teardown", action="store_true")
    a = parser.parse_args()
    p = a.profile

    user = cli(p, "current-user", "me")["userName"]
    folder = f"/Workspace/Users/{user}/poc/scd2-history-migration/notebooks"
    remote = f"{folder}/{Path(a.notebook).stem}"
    cli(p, "workspace", "mkdirs", folder)
    cli(p, "workspace", "import", remote, "--file", a.notebook, "--format", "SOURCE", "--language", "PYTHON", "--overwrite")
    spec = {
        "run_name": f"poc {Path(a.notebook).stem}",
        "tasks": [{
            "task_key": "notebook",
            "notebook_task": {"notebook_path": remote, "base_parameters": {"teardown": str(a.teardown).lower()}},
            "max_retries": 0,
        }],
    }
    run_id = str(cli(p, "jobs", "submit", "--json", json.dumps(spec), "--no-wait")["run_id"])
    print("run", run_id)
    while True:
        run = cli(p, "jobs", "get-run", run_id)
        if run["state"].get("life_cycle_state") in ("TERMINATED", "INTERNAL_ERROR", "SKIPPED"):
            break
        time.sleep(30)
    print(run["state"])
    task_run_id = str(run["tasks"][0]["run_id"])
    outputs(p, task_run_id)
    error = cli(p, "jobs", "get-run-output", task_run_id)
    if error.get("error"):
        print("ERROR:", error["error"][:1500])


if __name__ == "__main__":
    main()
