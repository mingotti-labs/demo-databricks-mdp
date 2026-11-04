"""Create, run and report a throwaway pipeline for probe P1; --delete removes it afterwards.

Usage: uv run python run.py --profile <PROFILE> [--delete <pipeline_id>]
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).parent


def cli(*args: str, profile: str) -> str:
    result = subprocess.run(
        ["databricks", *args, "--profile", profile, "-o", "json"], capture_output=True, text=True, check=True
    )
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--delete")
    args = parser.parse_args()
    if args.delete:
        subprocess.run(["databricks", "pipelines", "delete", args.delete, "--profile", args.profile], check=True)
        return
    user = json.loads(cli("current-user", "me", profile=args.profile))["userName"]
    remote = f"/Workspace/Users/{user}/poc/market-climate-silver"
    cli("workspace", "import-dir", str(HERE), remote, "--overwrite", profile=args.profile)
    spec = {
        "name": "poc--market-climate-silver--p1",
        "catalog": "mdp_dev",
        "schema": "pattern_bronze",
        "serverless": True,
        "libraries": [{"file": {"path": f"{remote}/p1_comments.py"}}],
    }
    pipeline_id = json.loads(cli("pipelines", "create", "--json", json.dumps(spec), profile=args.profile))["pipeline_id"]
    update_id = json.loads(cli("pipelines", "start-update", pipeline_id, profile=args.profile))["update_id"]
    while True:
        state = json.loads(cli("pipelines", "get-update", pipeline_id, update_id, profile=args.profile))["update"]["state"]
        if state in ("COMPLETED", "FAILED", "CANCELED"):
            break
        time.sleep(15)
    print(pipeline_id, state)


if __name__ == "__main__":
    main()
