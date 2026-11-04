"""Probe P2 (market-climate-dashboard, read only): the member valuation query on the latest day in dev.

Prints rows per day, used and excluded counts by reason, and the five members pushing the P/E up and down most.
Usage: uv run python p2_member_sanity.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from common.market_climate_sql import DOMAIN, index_member_valuation_query  # noqa: E402
from p1_old_vs_new import cli, sql  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    q = index_member_valuation_query().replace(f"{DOMAIN}.", f"{args.catalog}.{DOMAIN}.")
    latest = f"valuation_date = (SELECT max(valuation_date) FROM m)"
    runs = {
        "rows, days": f"WITH m AS ({q}) SELECT count(*), count(DISTINCT valuation_date) FROM m",
        "latest day by reason": f"WITH m AS ({q}) SELECT coalesce(exclusion_reason_code, 'used'), count(*) FROM m WHERE {latest} GROUP BY 1 ORDER BY 2 DESC",
        "up most": f"WITH m AS ({q}) SELECT company_id, price_earnings_ten_year_average_inflation_adjusted_ratio, market_value_share_ratio, price_earnings_without_member_ratio, price_earnings_effect_ratio FROM m WHERE {latest} ORDER BY price_earnings_effect_ratio DESC LIMIT 5",
        "down most": f"WITH m AS ({q}) SELECT company_id, price_earnings_ten_year_average_inflation_adjusted_ratio, market_value_share_ratio, price_earnings_without_member_ratio, price_earnings_effect_ratio FROM m WHERE {latest} ORDER BY price_earnings_effect_ratio ASC LIMIT 5",
    }
    for name, statement in runs.items():
        print(name)
        for row in sql(args.profile, warehouse, statement):
            print("  ", row)


if __name__ == "__main__":
    main()
