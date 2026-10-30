"""Upload the probe folder and run one probe as a one-time serverless job.

Usage: uv run python run.py <probe> --profile <PROFILE>
"""

import argparse
import json
import shutil
import subprocess
import tempfile
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
    parser.add_argument("probe", help="script name without .py, e.g. p1_api")
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()

    user = json.loads(cli("current-user", "me", profile=args.profile))["userName"]
    remote = f"/Workspace/Users/{user}/poc/fred-rates"
    with tempfile.TemporaryDirectory() as staging:
        for script in HERE.glob("p*.py"):
            shutil.copy(script, staging)
        cli(
            "workspace",
            "import-dir",
            staging,
            remote,
            "--overwrite",
            profile=args.profile,
        )

    body = {
        "run_name": f"poc--fred-rates--{args.probe}",
        "tasks": [
            {
                "task_key": args.probe,
                "spark_python_task": {
                    "python_file": f"{remote}/{args.probe}.py",
                    "parameters": [remote],
                },
                "environment_key": "default",
            }
        ],
        "environments": [
            {"environment_key": "default", "spec": {"environment_version": "4"}}
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
    output = json.loads(
        cli(
            "jobs",
            "get-run-output",
            str(run["tasks"][0]["run_id"]),
            profile=args.profile,
        )
    )
    print(run["state"].get("result_state"), run["run_page_url"])
    print(output.get("logs", ""))
    if output.get("error"):
        print(output["error"], output.get("error_trace", ""))


if __name__ == "__main__":
    main()
