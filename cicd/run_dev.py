"""Run a unit in dev as the CI/CD service principal, by job id.

The PR's deploy-dev deploys the bundle as the SP, which prefixes its dev copies
with `[dev svc_cicd_github]`. A job runs as its owner whoever triggers it, so
running the SP's `run--<unit>--dev` by id executes it as the SP.

Usage: uv run python cicd/run_dev.py <unit> --profile <PROFILE> [--param key=value ...]
"""

import argparse
import json
import subprocess
import sys
import time

SP_PREFIX = "[dev svc_cicd_github]"
ENDED = ("TERMINATED", "SKIPPED", "INTERNAL_ERROR")


def job_name(unit: str) -> str:
    """The SP's dev copy of the unit's run job."""
    return f"{SP_PREFIX} run--{unit}--dev"


def run_payload(job_id: int, params: list[str]) -> dict:
    """`jobs run-now` body with `key=value` pairs as job parameters."""
    pairs = dict(param.split("=", 1) for param in params)
    return {"job_id": job_id, "job_parameters": pairs}


def find_job_id(jobs: list[dict], name: str) -> int | None:
    """The id of the job named exactly `name`, if any."""
    ids = [job["job_id"] for job in jobs if job["settings"]["name"] == name]
    return ids[0] if ids else None


def cli(profile: str, *args: str) -> dict | list:
    result = subprocess.run(
        ["databricks", *args, "--profile", profile, "-o", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("unit", help="unit name, e.g. yahoo for run_yahoo")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--param", action="append", default=[], help="key=value")
    args = parser.parse_args()

    name = job_name(args.unit)
    job_id = find_job_id(cli(args.profile, "jobs", "list", "--name", name), name)
    if job_id is None:
        sys.exit(f"No job '{name}': open the PR so deploy-dev deploys it as the SP.")
    payload = json.dumps(run_payload(job_id, args.param))
    run_id = cli(args.profile, "jobs", "run-now", "--json", payload, "--no-wait")[
        "run_id"
    ]
    print(f"{name}: run {run_id}")
    while (run := cli(args.profile, "jobs", "get-run", str(run_id)))["state"][
        "life_cycle_state"
    ] not in ENDED:
        time.sleep(30)
    result = run["state"].get("result_state")
    print(result, run["run_page_url"])
    if result != "SUCCESS":
        sys.exit(1)


if __name__ == "__main__":
    main()
