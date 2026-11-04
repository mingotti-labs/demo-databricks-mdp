"""Probe P3 (read only): why members of several share classes have no share count.

For NKE, MA, UPS, FOXA and HSY: the share facts SEC sent (Landing) for their latest filings, and
what company_fundamentals kept.

Usage: uv run python p3_shares.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "single-silver-landing-schema"))
from compare import cli, sql  # noqa: E402

SYMBOLS = "('NKE', 'MA', 'UPS', 'FOXA', 'HSY')"
QUERIES = {
    "latest filing kept per company (form, filed, shares)": """
        SELECT l.trading_symbol_code, f.form_code, f.valid_from_date, f.shares_outstanding_count, f.accession_number
        FROM {d}.company_fundamentals f JOIN {d}.listing l USING (company_id)
        WHERE l.trading_symbol_code IN {sym} AND f.valid_to_date = DATE '9999-12-31' ORDER BY 1""",
    "share facts in Landing for those accessions (concept, end, value, rows)": """
        WITH latest AS (
          SELECT l.trading_symbol_code, f.accession_number FROM {d}.company_fundamentals f JOIN {d}.listing l USING (company_id)
          WHERE l.trading_symbol_code IN {sym} AND f.valid_to_date = DATE '9999-12-31')
        SELECT x.trading_symbol_code, c.concept, c.unit, c.end, c.form, c.val, count(*) OVER (PARTITION BY x.trading_symbol_code, c.concept, c.end) AS same_end_rows
        FROM {c}.silver_landing.sec__company_facts c JOIN latest x ON x.accession_number = c.accn
        WHERE c.is_current AND c.concept IN ('EntityCommonStockSharesOutstanding', 'CommonStockSharesOutstanding')
        ORDER BY 1, 2, 4""",
    "any share facts ever for these companies (concept, rows, last end, last value)": """
        WITH ciks AS (SELECT DISTINCT l.trading_symbol_code, co.central_index_key FROM {d}.listing l JOIN {d}.company co USING (company_id)
                      WHERE l.trading_symbol_code IN {sym})
        SELECT x.trading_symbol_code, c.concept, count(*), max(c.end), max_by(c.val, c.end)
        FROM {c}.silver_landing.sec__company_facts c JOIN ciks x ON ltrim('0', x.central_index_key) = ltrim('0', c.cik)
        WHERE c.is_current AND c.concept IN ('EntityCommonStockSharesOutstanding', 'CommonStockSharesOutstanding')
        GROUP BY 1, 2 ORDER BY 1, 2""",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    for title, query in QUERIES.items():
        print(f"== {title}")
        text = query.format(d=f"{args.catalog}.silver_domain_investments", c=args.catalog, sym=SYMBOLS)
        for row in sql(args.profile, warehouse, text):
            print("  ", row)


if __name__ == "__main__":
    main()
