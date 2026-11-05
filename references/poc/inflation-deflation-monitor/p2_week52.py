"""Probe P2b (inflation-deflation-monitor, read only): the 52-week window of price_indicator_daily on EQT.

Runs the pipeline's window on `price_daily` of a catalog and compares it with the dashboard's current figures.
Usage: uv run python p2_week52.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse

from probe import run

QUERY = """
SELECT p.price_date, p.price_close,
       max(p.price_high) OVER w AS high_52, min(p.price_low) OVER w AS low_52
FROM {c}.silver_domain_investments.price_daily p
JOIN {c}.silver_domain_investments.listing l ON l.listing_id = p.listing_id
JOIN {c}.silver_domain_investments.company co ON co.company_id = l.company_id
WHERE co.company_name = 'EQT Corporation'
WINDOW w AS (PARTITION BY p.listing_id ORDER BY CAST(p.price_date AS TIMESTAMP) RANGE BETWEEN INTERVAL 363 DAYS PRECEDING AND CURRENT ROW)
QUALIFY row_number() OVER (ORDER BY p.price_date DESC) <= 2
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    print("window result (date, close, 52-week high, 52-week low):")
    for row in run(args.profile, QUERY.format(c=args.catalog)):
        print("  ", row)
    print("dashboard figures on 2026-11-03 (12 months, price_date > 2025-11-03): high 68.239998, low 47.939999")


if __name__ == "__main__":
    main()
