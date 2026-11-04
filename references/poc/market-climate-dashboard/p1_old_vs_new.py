"""Probe P1 (market-climate-dashboard, read only): the new gold queries against the old tables.

The member query summed by the new index query must equal `index_valuation_daily` (every column but
`ingested_timestamp`, then the timestamps), and the new signal query on that sum must equal
`monitor_signal_daily`. Run after the new tables exist (with --tables) to compare the tables themselves.

Usage: uv run python p1_old_vs_new.py --profile <PROFILE> [--catalog mdp_dev] [--tables]
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "references" / "poc" / "single-silver-landing-schema"))
from common.market_climate_signals_sql import monitor_signal_query  # noqa: E402
from common.market_climate_sql import DOMAIN, index_member_valuation_query, index_valuation_query  # noqa: E402
from compare import cli  # noqa: E402


def sql(profile: str, warehouse: str, statement: str) -> list[list]:
    """Run a statement on the warehouse; the body goes through a file (the text is longer than a Windows command line)."""
    body = {"warehouse_id": warehouse, "statement": statement, "wait_timeout": "50s"}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(body, f)
    out = cli(profile, "api", "post", "/api/2.0/sql/statements", "--json", f"@{f.name}")
    while out["status"]["state"] in ("PENDING", "RUNNING"):
        out = cli(profile, "api", "get", f"/api/2.0/sql/statements/{out['statement_id']}")
    if out["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(out["status"])
    return out["result"].get("data_array") or []


def only(a: str, b: str, skip: str) -> str:
    row = f"to_json(struct(* EXCEPT({skip})))"
    return f"(SELECT count(*) FROM (SELECT {row} FROM {a} EXCEPT ALL SELECT {row} FROM {b}))"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    parser.add_argument("--tables", action="store_true", help="compare the new tables, not the queries")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    gold = f"{args.catalog}.gold_analytics_gateway"
    qualify = lambda q: q.replace(f"{DOMAIN}.", f"{args.catalog}.{DOMAIN}.")  # noqa: E731
    if args.tables:
        new_index, new_signal = f"{gold}.valuation_daily_index", f"{gold}.monitor_daily_signal"
    else:
        member = index_member_valuation_query()
        index_text = index_valuation_query(f"({member})")
        new_index = f"({qualify(index_text)})"
        new_signal = f"({qualify(monitor_signal_query(f'({index_text})'))})"
    old_index, old_signal = f"{gold}.index_valuation_daily", f"{gold}.monitor_signal_daily"
    for name, old, new in (("index", old_index, new_index), ("signal", old_signal, new_signal)):
        row = sql(args.profile, warehouse, (
            f"SELECT (SELECT count(*) FROM {old}), (SELECT count(*) FROM {new}), "
            f"{only(old, new, 'ingested_timestamp')}, {only(new, old, 'ingested_timestamp')}, "
            f"(SELECT count(*) FROM {old} o JOIN {new} n USING ({'valuation_date' if name == 'index' else 'signal_date, monitor_code, lens_code, signal_code'}) "
            f"WHERE o.ingested_timestamp <=> n.ingested_timestamp)"
        ))[0]
        print(f"{name}: old rows {row[0]}, new rows {row[1]}, only old {row[2]}, only new {row[3]}, same timestamp {row[4]}")


if __name__ == "__main__":
    main()
