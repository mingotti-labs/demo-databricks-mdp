"""Probe P2 (market-climate-genie, read only): every example and benchmark SQL of the Genie agent on the warehouse.

The committed agent file holds `${var.catalog}`; the bundle fills it in per target, so here it is replaced by the catalog.

Usage: uv run python p2_run_examples.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "references" / "poc" / "single-silver-landing-schema"))
from compare import cli  # noqa: E402

AGENT = ROOT / "resources" / "genie" / "market_climate.genie.yml"


def run(profile: str, warehouse: str, statement: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"warehouse_id": warehouse, "statement": statement, "wait_timeout": "50s"}, f)
    out = cli(profile, "api", "post", "/api/2.0/sql/statements", "--json", f"@{f.name}")
    while out["status"]["state"] in ("PENDING", "RUNNING"):
        out = cli(profile, "api", "get", f"/api/2.0/sql/statements/{out['statement_id']}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    space = json.loads(AGENT.read_text(encoding="utf-8"))["resources"]["genie_spaces"]["market_climate_genie"]["serialized_space"]
    items = [("example", e["question"][0], e["sql"][0]) for e in space["instructions"]["example_question_sqls"]]
    items += [("benchmark", b["question"][0], b["answer"][0]["content"][0]) for b in space["benchmarks"]["questions"]]
    for kind, question, sql in items:
        out = run(args.profile, warehouse, sql.replace("${var.catalog}", args.catalog))
        state = out["status"]["state"]
        rows = out.get("result", {}).get("data_array") or []
        print(f"== {kind}: {question}: {state}, rows {out.get('manifest', {}).get('total_row_count')}")
        if state != "SUCCEEDED":
            print("  ", out["status"].get("error", {}).get("message", "")[:300])
        for row in rows[:2]:
            print("  ", row)


if __name__ == "__main__":
    main()
