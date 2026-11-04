"""Probe P5 (read only): share count coverage of the current index members, after shares-outstanding-all-classes.

Usage: uv run python p5_share_coverage.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "single-silver-landing-schema"))
from compare import cli, sql  # noqa: E402

QUERIES = {
    "current members: companies, with cover count, with weighted average, with either, with neither": """
        WITH m AS (SELECT DISTINCT l.company_id FROM {s}.index_membership x JOIN {s}.listing l USING (listing_id) WHERE x.is_current),
        f AS (SELECT * FROM {s}.company_fundamentals WHERE valid_to_date = DATE '9999-12-31')
        SELECT count(*), count_if(f.shares_outstanding_count IS NOT NULL), count_if(f.weighted_average_shares_basic_count IS NOT NULL),
               count_if(coalesce(f.shares_outstanding_count, f.weighted_average_shares_basic_count) IS NOT NULL),
               count_if(coalesce(f.shares_outstanding_count, f.weighted_average_shares_basic_count) IS NULL)
        FROM m LEFT JOIN f USING (company_id)""",
    "members with neither count": """
        WITH m AS (SELECT DISTINCT l.company_id, l.trading_symbol_code FROM {s}.index_membership x JOIN {s}.listing l USING (listing_id) WHERE x.is_current),
        f AS (SELECT * FROM {s}.company_fundamentals WHERE valid_to_date = DATE '9999-12-31')
        SELECT m.trading_symbol_code, f.form_code, f.valid_from_date FROM m LEFT JOIN f USING (company_id)
        WHERE coalesce(f.shares_outstanding_count, f.weighted_average_shares_basic_count) IS NULL ORDER BY 1""",
    "sample (MA, NKE, UPS, FOXA, HSY, GOOGL, AAPL): form, filed, cover, weighted average": """
        SELECT l.trading_symbol_code, f.form_code, f.valid_from_date, f.shares_outstanding_count, f.weighted_average_shares_basic_count
        FROM {s}.company_fundamentals f JOIN {s}.listing l USING (company_id)
        WHERE f.valid_to_date = DATE '9999-12-31' AND l.trading_symbol_code IN ('MA','NKE','UPS','FOXA','HSY','GOOGL','AAPL') ORDER BY 1""",
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
