"""Probe P2 (read only): the new columns with real data, in dev or prd.

Usage: uv run python p2_results.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "single-silver-landing-schema"))
from compare import cli, sql  # noqa: E402

QUERIES = {
    "Apple, latest 10-K row: filed, period end, years, CPI, plain avg bn, inflation-adjusted avg bn": """
        SELECT f.valid_from_date, f.period_end_date, f.earnings_year_count, f.consumer_price_index_value,
               round(f.earnings_ten_year_average_amount / 1e9, 2), round(f.earnings_ten_year_average_inflation_adjusted_amount / 1e9, 2)
        FROM {s}.company_fundamentals f JOIN {s}.company c USING (company_id)
        WHERE c.company_name = 'Apple Inc.' AND f.form_code LIKE '10-K%'
        ORDER BY f.valid_from_date DESC LIMIT 2""",
    "years of earnings per current member: years, members": """
        SELECT f.earnings_year_count, count(*) FROM {s}.company_fundamentals f
        WHERE f.valid_to_date = DATE '9999-12-31' GROUP BY 1 ORDER BY 1""",
    "^GSPC: first price date, last price date, rows, latest close, 200-day average, slope": """
        SELECT min(price_date), max(price_date), count(*), max_by(price_close_adjusted, price_date),
               max_by(close_adjusted_two_hundred_day_average_amount, price_date),
               max_by(close_adjusted_two_hundred_day_average_slope_ratio, price_date)
        FROM {s}.price_indicator_daily WHERE trading_symbol_code = '^GSPC'""",
    "price_indicator_daily rows, with an average, with a slope": """
        SELECT count(*), count(close_adjusted_two_hundred_day_average_amount), count(close_adjusted_two_hundred_day_average_slope_ratio)
        FROM {s}.price_indicator_daily""",
    "SPY (a member-like listing with one year of prices): rows, with an average": """
        SELECT count(*), count(close_adjusted_two_hundred_day_average_amount) FROM {s}.price_indicator_daily WHERE trading_symbol_code = 'SPY'""",
    "CPI used for a period ending in October 2025 (no value that month)": """
        SELECT period_end_date, consumer_price_index_value FROM {s}.company_fundamentals
        WHERE period_end_date BETWEEN DATE '2025-10-01' AND DATE '2025-10-31' AND consumer_price_index_value IS NOT NULL LIMIT 3""",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    for title, query in QUERIES.items():
        print(f"== {title}")
        for row in sql(args.profile, warehouse, query.format(s=f"{args.catalog}.silver_domain_investments")):
            print("  ", row)


if __name__ == "__main__":
    main()
