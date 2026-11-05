"""Probe P2 (inflation-deflation-monitor, read only): the market_rate_indicator_daily query before it is deployed.

Usage: uv run python p2_market_rate_indicator.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
from pathlib import Path

from probe import run
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from common.inflation_sql import market_rate_indicator_query  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    prefix = f"{args.catalog}.silver_domain_investments."
    query = market_rate_indicator_query(prefix)
    show = lambda title, sql: print(f"== {title}\n", *run(args.profile, sql), sep="\n  ")  # noqa: E731
    show("rows per series", f"SELECT rate_code, count(*), min(indicator_date), max(indicator_date), "
                            f"count_if(two_hundred_day_average_value IS NOT NULL), count_if(two_hundred_day_average_change_value IS NOT NULL) "
                            f"FROM ({query}) GROUP BY 1 ORDER BY 1")
    show("CPI change against the previous reading, September 2026 (expect 0.585)",
         f"SELECT indicator_date, rate_value, observation_date FROM ({query}) WHERE rate_code = 'us_cpi_change_previous_reading_percent' "
         f"AND indicator_date IN (DATE '2026-08-31', DATE '2026-09-01', DATE '2026-09-02', DATE '2026-09-30') ORDER BY 1")
    show("latest row per series",
         f"SELECT rate_code, indicator_date, rate_value, observation_date, two_hundred_day_average_value, two_hundred_day_average_change_value "
         f"FROM ({query}) QUALIFY row_number() OVER (PARTITION BY rate_code ORDER BY indicator_date DESC) = 1 ORDER BY 1")
    show("federal funds 200-day average on 2026-09-30: query vs hand average (equal)",
         f"""WITH d AS (SELECT price_date FROM {prefix}price_daily WHERE trading_symbol_code = '^GSPC' AND price_date <= DATE '2026-09-30'
                       ORDER BY price_date DESC LIMIT 200)
             SELECT (SELECT two_hundred_day_average_value FROM ({query}) WHERE rate_code = 'us_federal_funds_effective_rate' AND indicator_date = DATE '2026-09-30') AS query_average,
                    (SELECT CAST(avg(m.rate_value) AS DECIMAL(18, 6)) FROM d JOIN {prefix}market_rate_daily m
                       ON m.rate_code = 'us_federal_funds_effective_rate' AND m.observation_date = d.price_date) AS hand_average""")
    show("real rate on 2026-09-30 = effective rate - CPI 12-month change",
         f"""SELECT max(CASE WHEN rate_code = 'us_real_federal_funds_rate' THEN rate_value END) AS real_rate,
                    max(CASE WHEN rate_code = 'us_federal_funds_effective_rate' THEN rate_value END)
                      - max(CASE WHEN rate_code = 'us_cpi_change_twelve_months_percent' THEN rate_value END) AS parts
             FROM ({query}) WHERE indicator_date = DATE '2026-09-30'""")


if __name__ == "__main__":
    main()
