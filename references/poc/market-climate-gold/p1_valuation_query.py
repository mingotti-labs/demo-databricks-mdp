"""Probe P1 (market-climate-gold, read only): run index_valuation_query() on the SQL warehouse.

Prints the first days, the last days and the day closest to the story's probe P1 (2026-11-02:
P/E 10-year inflation-adjusted 40.8, trailing 24.7, 458 members used).

Usage: uv run python p1_valuation_query.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "references" / "poc" / "single-silver-landing-schema"))
from common.market_climate_sql import DOMAIN, index_valuation_query  # noqa: E402
from compare import cli, sql  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    query = index_valuation_query().replace(f"{DOMAIN}.", f"{args.catalog}.{DOMAIN}.")
    columns = (
        "valuation_date, member_count, members_used_count, members_without_shares_count, "
        "members_under_ten_years_count, round(market_value_amount / 1e12, 3) AS market_value_tn, "
        "round(earnings_trailing_twelve_months_amount / 1e9) AS trailing_bn, "
        "round(earnings_ten_year_average_amount / 1e9) AS plain_bn, "
        "round(earnings_ten_year_average_inflation_adjusted_amount / 1e9) AS adjusted_bn, "
        "price_earnings_trailing_twelve_months_ratio, price_earnings_ten_year_average_ratio, "
        "price_earnings_ten_year_average_inflation_adjusted_ratio, consumer_price_index_value"
    )
    print("valuation_date | members | used | no shares | under 10y | mv tn | trailing bn | plain bn | adj bn | pe trailing | pe plain10 | pe adj10 | cpi")
    for order in ("ASC", "DESC"):
        rows = sql(args.profile, warehouse, f"WITH v AS ({query}) SELECT {columns} FROM v ORDER BY valuation_date {order} LIMIT 3")
        for row in rows:
            print(" | ".join(str(x) for x in row))
        print("...")
    n = sql(args.profile, warehouse, f"WITH v AS ({query}) SELECT count(*), min(valuation_date), max(valuation_date) FROM v")
    print("days:", n[0])


if __name__ == "__main__":
    main()
