"""Claude Code PreToolUse hook: refuse a local deploy, run or destroy of the main bundle.

Dev runs go through the CI/CD service principal's dev copies (openspec
dev-runs-as-service-principal): a local deploy creates human-owned pipelines whose
tables the SP cannot take over. Reads the tool call as JSON on stdin; exit 2
refuses it and shows the message to the agent. The patterns bundle
(references/patterns), deployed by hand in dev, is allowed.
"""

import json
import re
import sys

BUNDLE_ACTION = re.compile(
    r"(^|[;&|(])\s*databricks\s+bundle\s+(deploy|run|destroy)\b", re.MULTILINE
)
PATTERNS = re.compile(r"references[/\\]patterns")
MESSAGE = (
    "Refused: do not deploy, run or destroy the main bundle locally. Push the branch "
    "and open the PR as a draft so deploy-dev deploys as the CI/CD service principal, "
    "then run its copy: uv run python cicd/run_dev.py <unit> --profile <PROFILE> "
    "[--param key=value]. See CONTRIBUTING.md, step 4."
)


def refusal(command: str, cwd: str) -> str | None:
    """The message to refuse with, or None when the command may run."""
    if not BUNDLE_ACTION.search(command):
        return None
    if PATTERNS.search(command) or PATTERNS.search(cwd):
        return None
    return MESSAGE


def main() -> None:
    call = json.load(sys.stdin)
    message = refusal(
        call.get("tool_input", {}).get("command", ""), call.get("cwd", "")
    )
    if message:
        print(message, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
