"""Probe P4 (market-climate-gold, read only): design_pattern tags and descriptions of the gold tables.

Usage: uv run python p4_tags.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "single-silver-landing-schema"))
from compare import cli, sql  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    print("table tags (table, tag, value):")
    for row in sql(args.profile, warehouse,
                   f"SELECT table_name, tag_name, tag_value FROM {args.catalog}.information_schema.table_tags "
                   "WHERE schema_name = 'gold_analytics_gateway' ORDER BY 1"):
        print("  ", row)
    print("sample column descriptions (column, description start):")
    for row in sql(args.profile, warehouse,
                   f"SELECT column_name, left(comment, 110) FROM {args.catalog}.information_schema.columns "
                   "WHERE table_schema = 'gold_analytics_gateway' AND table_name = 'index_valuation_daily' "
                   "AND column_name IN ('price_earnings_ten_year_average_inflation_adjusted_ratio', 'members_used_count') ORDER BY 1"):
        print("  ", row)


if __name__ == "__main__":
    main()
