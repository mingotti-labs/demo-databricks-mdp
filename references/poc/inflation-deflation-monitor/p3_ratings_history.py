"""Probe P3 (inflation-deflation-monitor, read only): the signal query over a catalog's history, before it is deployed.

Prints, per year, the days rated, the average stars, the days at -1 and at 4; and the stars on the latest day.
Usage: uv run python p3_ratings_history.py --profile <PROFILE> [--catalog mdp_prd]
"""

import argparse
import sys
from pathlib import Path

from probe import run

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from common.inflation_signals_sql import inflation_signal_query  # noqa: E402
from common.market_rate_indicator_sql import market_rate_indicator_query  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_prd")
    args = parser.parse_args()
    domain = f"{args.catalog}.silver_domain_investments"
    query = inflation_signal_query(domain, f"({market_rate_indicator_query(domain + '.')})")
    print("year, rated days, average stars, days at -1, days at 4, days at 0")
    for row in run(args.profile, f"""SELECT year(signal_date), count(*), round(avg(yes_count), 2),
        count_if(measured_value = -1), count_if(measured_value = 4), count_if(measured_value = 0)
        FROM ({query}) WHERE signal_code = 'rating' GROUP BY 1 ORDER BY 1"""):
        print("  ", row)
    print("rows per signal:", run(args.profile, f"SELECT signal_code, count(*), min(signal_date), max(signal_date) FROM ({query}) GROUP BY 1 ORDER BY 1"))
    print("latest day:")
    for row in run(args.profile, f"""SELECT signal_date, signal_code, is_yes, measured_value, threshold_value, yes_count, action_name, band_code
        FROM ({query}) WHERE signal_date = (SELECT max(signal_date) FROM ({query})) ORDER BY signal_code"""):
        print("  ", row)


if __name__ == "__main__":
    main()
