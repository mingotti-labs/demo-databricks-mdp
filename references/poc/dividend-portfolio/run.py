"""Upload the probe folder and run one probe as a one-time serverless job.

Usage: uv run python run.py <probe> --profile <PROFILE> [--deps pkg ...]
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
        if run["state"]["life_cycle_state"] in (
            "TERMINATED",
            "SKIPPED",
            "INTERNAL_ERROR",
        ):
            return run
        time.sleep(15)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("probe", help="script name without .py, e.g. p1_hosts")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--deps", nargs="*", default=[])
    args = parser.parse_args()

    user = json.loads(cli("current-user", "me", profile=args.profile))["userName"]
    remote = f"/Workspace/Users/{user}/poc/dividend-portfolio"
    cli(
        "workspace",
        "import-dir",
        str(HERE),
        remote,
        "--overwrite",
        profile=args.profile,
    )

    body = {
        "run_name": f"poc--dividend-portfolio--{args.probe}",
        "tasks": [
            {
                "task_key": args.probe,
                "spark_python_task": {"python_file": f"{remote}/{args.probe}.py"},
                "environment_key": "default",
            }
        ],
        "environments": [
            {
                "environment_key": "default",
                "spec": {"environment_version": "4", "dependencies": args.deps},
            }
        ],
    }
    submitted = json.loads(
        cli(
            "jobs",
            "submit",
            "--json",
            json.dumps(body),
            "--no-wait",
            profile=args.profile,
        )
    )
    run = wait(str(submitted["run_id"]), args.profile)
    task_run_id = str(run["tasks"][0]["run_id"])
    output = json.loads(
        cli("jobs", "get-run-output", task_run_id, profile=args.profile)
    )
    print(run["state"].get("result_state"), run["run_page_url"])
    print(output.get("logs", ""))
    if output.get("error"):
        print(output["error"], output.get("error_trace", ""))


if __name__ == "__main__":
    main()
