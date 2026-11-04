"""Probe P2 (read only): why P1's history is empty and why 41 members have no market value.

Usage: uv run python p2_gaps.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "single-silver-landing-schema"))
from compare import cli, sql  # noqa: E402

QUERIES = {
    "price history per member (min first date, members starting before 2020, max first date, members)": """
        WITH m AS (SELECT DISTINCT listing_id FROM {s}.index_membership WHERE is_current)
        SELECT min(first_date), count_if(first_date < DATE '2020-01-01'), max(first_date), count(*)
        FROM (SELECT p.listing_id, min(p.price_date) AS first_date FROM {s}.price_daily p JOIN m USING (listing_id) GROUP BY 1)""",
    "AAPL and ^GSPC-like benchmarks first price dates": """
        SELECT l.trading_symbol_code, min(p.price_date), count(*) FROM {s}.price_daily p JOIN {s}.listing l USING (listing_id)
        WHERE l.trading_symbol_code IN ('AAPL', 'SPY', 'MSFT') GROUP BY 1""",
    "members without market value: reason": """
        WITH m AS (SELECT DISTINCT l.company_id, l.trading_symbol_code FROM {s}.index_membership x JOIN {s}.listing l USING (listing_id) WHERE x.is_current),
        f AS (SELECT company_id, shares_outstanding_count FROM {s}.company_fundamentals WHERE valid_to_date = DATE '9999-12-31')
        SELECT CASE WHEN m.company_id IS NULL THEN 'no company_id'
                    WHEN f.company_id IS NULL THEN 'no fundamentals row'
                    WHEN f.shares_outstanding_count IS NULL THEN 'no shares on latest filing'
                    ELSE 'has shares' END AS reason, count(*), slice(collect_list(m.trading_symbol_code), 1, 12)
        FROM m LEFT JOIN f USING (company_id) GROUP BY 1""",
    "members with shares on an older filing but not the latest": """
        WITH m AS (SELECT DISTINCT l.company_id FROM {s}.index_membership x JOIN {s}.listing l USING (listing_id) WHERE x.is_current),
        latest AS (SELECT company_id FROM {s}.company_fundamentals WHERE valid_to_date = DATE '9999-12-31' AND shares_outstanding_count IS NULL)
        SELECT count(DISTINCT f.company_id) FROM {s}.company_fundamentals f JOIN latest USING (company_id) JOIN m USING (company_id)
        WHERE f.shares_outstanding_count IS NOT NULL""",
    "10-K years available per member (min years, median years, max years, earliest year end, members with a year end by 2016)": """
        WITH m AS (SELECT DISTINCT l.company_id FROM {s}.index_membership x JOIN {s}.listing l USING (listing_id) WHERE x.is_current),
        k AS (SELECT company_id, count(DISTINCT period_end_date) AS n, min(period_end_date) AS first_end
              FROM {s}.company_fundamentals WHERE form_code LIKE '10-K%' AND net_income IS NOT NULL GROUP BY 1)
        SELECT min(n), percentile_disc(0.5) WITHIN GROUP (ORDER BY n), max(n), min(first_end), count_if(first_end <= DATE '2016-12-31')
        FROM m JOIN k USING (company_id)""",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    schema = f"{args.catalog}.silver_domain_investments"
    for title, query in QUERIES.items():
        print(f"== {title}")
        for row in sql(args.profile, warehouse, query.format(s=schema)):
            print("  ", row)


if __name__ == "__main__":
    main()
