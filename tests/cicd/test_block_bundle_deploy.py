"""Tests for cicd/block_bundle_deploy.py, one per scenario of the dev-verification spec."""

import json
import subprocess
import sys
from pathlib import Path

from block_bundle_deploy import refusal

REPO = "C:/Workspace/labs/mingotti-works/demo-databricks-mdp"
HOOK = Path(__file__).parents[2] / "cicd" / "block_bundle_deploy.py"


def test_dev_deploy_refused():
    assert refusal("databricks bundle deploy -t dev --profile DEFAULT", REPO)


def test_default_target_run_refused():
    assert refusal("databricks bundle run run_yahoo --profile DEFAULT", REPO)


def test_prd_and_destroy_refused():
    assert refusal("databricks bundle deploy --target prd", REPO)
    assert refusal("cd x && databricks  bundle destroy -t dev", REPO)


def test_patterns_bundle_allowed():
    assert (
        refusal("databricks bundle deploy -t dev", f"{REPO}/references/patterns")
        is None
    )
    assert (
        refusal("cd references/patterns && databricks bundle deploy -t dev", REPO)
        is None
    )
    assert (
        refusal("databricks bundle deploy -t dev", f"{REPO}\\references\\patterns")
        is None
    )


def test_other_commands_allowed():
    assert refusal("databricks bundle validate -t dev", REPO) is None
    assert refusal("databricks jobs run-now 123 --profile DEFAULT", REPO) is None
    assert (
        refusal("uv run python cicd/run_dev.py yahoo --profile DEFAULT", REPO) is None
    )


def test_hook_exit_codes():
    def run(command):
        call = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": REPO}
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(call),
            capture_output=True,
            text=True,
            check=False,
        )

    refused = run("databricks bundle deploy -t dev")
    assert refused.returncode == 2 and "run_dev.py" in refused.stderr
    assert run("databricks bundle validate -t dev").returncode == 0
