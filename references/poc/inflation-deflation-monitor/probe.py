"""Helper for the inflation-deflation-monitor probes (read only): run a statement on the first SQL warehouse."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "references" / "poc" / "single-silver-landing-schema"))
from compare import cli  # noqa: E402


def run(profile: str, statement: str, warehouse: str | None = None) -> list[list]:
    """Rows of the statement; the body goes through a file (the text is longer than a Windows command line)."""
    warehouse = warehouse or cli(profile, "warehouses", "list")[0]["id"]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"warehouse_id": warehouse, "statement": statement, "wait_timeout": "50s"}, f)
    out = cli(profile, "api", "post", "/api/2.0/sql/statements", "--json", f"@{f.name}")
    while out["status"]["state"] in ("PENDING", "RUNNING"):
        out = cli(profile, "api", "get", f"/api/2.0/sql/statements/{out['statement_id']}")
    if out["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(out["status"].get("error", {}).get("message", out["status"]))
    return out.get("result", {}).get("data_array") or []
