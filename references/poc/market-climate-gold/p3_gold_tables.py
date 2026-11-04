"""Probe P3 (market-climate-gold, read only): the gold tables as built, in dev or prd.

Usage: uv run python p3_gold_tables.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "single-silver-landing-schema"))
from compare import cli, sql  # noqa: E402

QUERIES = {
    "valuation rows, first day, last day": "SELECT count(*), min(valuation_date), max(valuation_date) FROM {g}.index_valuation_daily",
    "latest valuation day": (
        "SELECT valuation_date, member_count, members_used_count, members_without_shares_count, members_under_ten_years_count, "
        "round(market_value_amount / 1e12, 3), round(earnings_trailing_twelve_months_amount / 1e9), "
        "round(earnings_ten_year_average_amount / 1e9), round(earnings_ten_year_average_inflation_adjusted_amount / 1e9), "
        "price_earnings_trailing_twelve_months_ratio, price_earnings_ten_year_average_ratio, "
        "price_earnings_ten_year_average_inflation_adjusted_ratio, consumer_price_index_value "
        "FROM {g}.index_valuation_daily ORDER BY valuation_date DESC LIMIT 1"
    ),
    "signal rows per lens and signal: first, last, rows": (
        "SELECT lens_code, signal_code, min(signal_date), max(signal_date), count(*) FROM {g}.monitor_signal_daily GROUP BY 1, 2 ORDER BY 1, 2"
    ),
    "latest climate rows": (
        "SELECT signal_date, lens_name, band_code, yes_count, action_name, reason_text FROM {g}.monitor_signal_daily "
        "WHERE signal_code = 'climate' AND signal_date = (SELECT max(signal_date) FROM {g}.monitor_signal_daily WHERE signal_code = 'climate') ORDER BY lens_code"
    ),
    "climate lights over the valuation history: lens, light, days": (
        "SELECT lens_code, band_code, count(*) FROM {g}.monitor_signal_daily WHERE signal_code = 'climate' GROUP BY 1, 2 ORDER BY 1, 2"
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    for title, query in QUERIES.items():
        print(f"== {title}")
        for row in sql(args.profile, warehouse, query.format(g=f"{args.catalog}.gold_analytics_gateway")):
            print("  ", " | ".join(str(x) for x in row))


if __name__ == "__main__":
    main()
