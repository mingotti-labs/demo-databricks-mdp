"""Probe P3 (market-climate-dashboard, read only): every dataset query of the dashboards (Market Climate and,
since inflation-deflation-monitor, Inflation Deflation) on the SQL warehouse.

Runs each query with the dashboard's own catalog and schema defaults (bare table names), with the date
parameter and the sector parameter bound to values. Prints rows and the first rows.

Usage: uv run python p3_test_queries.py --profile <PROFILE> [--catalog mdp_dev] [--as-of 2026-11-03] [--sector "Information Technology"]
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "single-silver-landing-schema"))
from compare import cli  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from common.currency_queries import DATASETS as CURRENCY_DATASETS  # noqa: E402
from common.inflation_queries import DATASETS as INFLATION_DATASETS  # noqa: E402
from common.market_climate_queries import DATASETS  # noqa: E402
from common.strategy_queries import DATASETS as STRATEGY_DATASETS  # noqa: E402


def run(profile: str, warehouse: str, catalog: str, statement: str, parameters: list[dict]) -> dict:
    body = {"warehouse_id": warehouse, "statement": statement, "wait_timeout": "50s", "catalog": catalog,
            "schema": "gold_analytics_gateway", "parameters": parameters}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(body, f)
    out = cli(profile, "api", "post", "/api/2.0/sql/statements", "--json", f"@{f.name}")
    while out["status"]["state"] in ("PENDING", "RUNNING"):
        out = cli(profile, "api", "get", f"/api/2.0/sql/statements/{out['statement_id']}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    parser.add_argument("--as-of", default=None, help="date for :as_of_date (default: today)")
    parser.add_argument("--sector", default="Information Technology")
    parser.add_argument("--company", default="EQT Corporation")
    parser.add_argument("--range", default="6M")
    parser.add_argument("--history-range", default="36M")
    parser.add_argument("--currency", default="CHF")
    parser.add_argument("--base", default="AUD")
    parser.add_argument("--fund", default="SQQQ")
    parser.add_argument("--only-strategy", action="store_true", help="run only the Strategy Monitor datasets")
    parser.add_argument("--setup-period", default="all")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    as_of = args.as_of or __import__("datetime").date.today().isoformat()
    parameters = [
        {"name": "as_of_date", "value": as_of, "type": "DATE"},
        {"name": "sector_name", "value": args.sector, "type": "STRING"},
        {"name": "company_name", "value": args.company, "type": "STRING"},
        {"name": "range_code", "value": args.range, "type": "STRING"},
        {"name": "history_range_code", "value": args.history_range, "type": "STRING"},
        {"name": "currency_code", "value": args.currency, "type": "STRING"},
        {"name": "base_code", "value": args.base, "type": "STRING"},
        {"name": "fund_code", "value": args.fund, "type": "STRING"},
        {"name": "setup_period", "value": args.setup_period, "type": "STRING"},
    ]
    every = STRATEGY_DATASETS if args.only_strategy else {**DATASETS, **INFLATION_DATASETS, **CURRENCY_DATASETS, **STRATEGY_DATASETS}
    for name, (title, query) in every.items():
        out = run(args.profile, warehouse, args.catalog, query, parameters)
        state = out["status"]["state"]
        print(f"== {name} ({title}): {state}")
        if state != "SUCCEEDED":
            print("  ", out["status"].get("error", {}).get("message", "")[:400])
            continue
        columns = [c["name"] for c in out["manifest"]["schema"]["columns"]]
        rows = out["result"].get("data_array") or []
        print("  columns:", columns)
        print("  rows:", out["manifest"].get("total_row_count"))
        for row in rows[:3]:
            print("  ", row)


if __name__ == "__main__":
    main()
