"""Probe P3 (read only): price_daily vs price_indicator_daily row counts, to show a prd/dev difference comes from the input.

Usage: uv run python p3_row_counts.py --profile <PROFILE>
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "single-silver-landing-schema"))
from compare import cli, sql  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    for catalog in ("mdp_prd", "mdp_dev"):
        s = f"{catalog}.silver_domain_investments"
        query = (
            f"SELECT (SELECT count(*) FROM {s}.price_daily), (SELECT count(*) FROM {s}.price_indicator_daily), "
            f"(SELECT count(*) FROM {s}.price_daily WHERE trading_symbol_code = 'SPY'), "
            f"(SELECT min(price_date) FROM {s}.price_daily WHERE trading_symbol_code = 'SPY'), "
            f"(SELECT count(DISTINCT listing_id) FROM {s}.price_daily)"
        )
        print(catalog, "price_daily rows, indicator rows, SPY rows, SPY first date, listings:", sql(args.profile, warehouse, query)[0])


if __name__ == "__main__":
    main()
