"""Upload the probe folder and run one probe notebook as a one-time serverless job.

The notebook's exit value is printed and saved to <probe>_result.txt; the run page keeps
the notebook with its tables.

Usage: uv run python run.py <probe> --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).parent


def cli(*args: str, profile: str) -> str:
    """Run a Databricks CLI command and return its stdout."""
    result = subprocess.run(
        ["databricks", *args, "--profile", profile, "-o", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def wait(run_id: str, profile: str) -> dict:
    """Poll a run until it terminates, whatever its result, and return it."""
    while True:
        run = json.loads(cli("jobs", "get-run", run_id, profile=profile))
        if run["state"]["life_cycle_state"] in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR"):
            return run
        time.sleep(15)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("probe", help="notebook name without .py, e.g. p1_pe10_examples")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()

    user = json.loads(cli("current-user", "me", profile=args.profile))["userName"]
    remote = f"/Workspace/Users/{user}/poc/market-climate"
    cli("workspace", "import-dir", str(HERE), remote, "--overwrite", profile=args.profile)

    body = {
        "run_name": f"poc--market-climate--{args.probe}",
        "tasks": [
            {
                "task_key": args.probe,
                "notebook_task": {
                    "notebook_path": f"{remote}/{args.probe}",
                    "base_parameters": {"catalog": args.catalog},
                },
            }
        ],
    }
    submitted = json.loads(
        cli("jobs", "submit", "--json", json.dumps(body), "--no-wait", profile=args.profile)
    )
    run = wait(str(submitted["run_id"]), args.profile)
    task_run_id = str(run["tasks"][0]["run_id"])
    output = json.loads(cli("jobs", "get-run-output", task_run_id, profile=args.profile))
    print(run["state"].get("result_state"), run["run_page_url"])
    result = output.get("notebook_output", {}).get("result", "")
    if result:
        print(result)
        (HERE / f"{args.probe}_result.txt").write_text(result + "\n", encoding="utf-8")
    if output.get("error"):
        print(output["error"], output.get("error_trace", ""))


if __name__ == "__main__":
    main()
