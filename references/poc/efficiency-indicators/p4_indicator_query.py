"""E4: run the price_indicator_daily query text on prd's price_daily (read only) and check the strategy 004 columns.

Usage: uv run python references/poc/efficiency-indicators/p4_indicator_query.py --profile DEFAULT --warehouse <id>
Prints the highest efficiency ratios of the S&P 500 members on the latest day (equals probe E3 for r60 within rounding),
a gap example and the row count against price_daily.
"""

import argparse
import re
import subprocess
from pathlib import Path

SOURCE = Path(__file__).parents[3] / "src/layers/silver/domain/investments/price_indicator_daily.py"
PRICE_DAILY = "mdp_prd.silver_domain_investments.price_daily"


def indicator_sql() -> str:
    text = SOURCE.read_text(encoding="utf-8")
    sql = re.search(r'spark\.sql\(\s*"""(.*?)"""', text, re.S).group(1)
    return sql.replace("FROM price_daily", f"FROM {PRICE_DAILY}")


def run(profile: str, warehouse: str, sql: str) -> str:
    result = subprocess.run(
        ["databricks", "experimental", "aitools", "tools", "query", "--profile", profile, "--output", "csv", sql],
        capture_output=True, text=True, env={**__import__("os").environ, "DATABRICKS_WAREHOUSE_ID": warehouse},
    )
    return result.stdout + result.stderr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="DEFAULT")
    parser.add_argument("--warehouse", required=True)
    args = parser.parse_args()
    q = indicator_sql()
    latest = "(SELECT max(price_date) FROM i WHERE trading_symbol_code = '^GSPC')"
    checks = {
        "rows (indicator vs price_daily)": f"WITH i AS ({q}) SELECT (SELECT count(*) FROM i) AS indicator_rows, (SELECT count(*) FROM {PRICE_DAILY}) AS price_rows",
        "top r60 and tr60 on the latest day": f"WITH i AS ({q}) SELECT max(efficiency_r60_ratio) AS r60_max, max(efficiency_tr60_ratio) AS tr60_max, count_if(efficiency_r60_ratio >= 15) AS r60_15, count_if(volume_sixty_day_average_count > 200000) AS volume_ok FROM i WHERE price_date = {latest}",
        "true range at least the range, equal on first rows": f"WITH i AS ({q}) SELECT count_if(true_range_amount < price_range_amount) AS true_below_range, count_if(true_range_amount > price_range_amount) AS gaps FROM i",
        "AAPL latest": f"WITH i AS ({q}) SELECT price_date, close_sixty_day_change_amount, price_range_sixty_day_average_amount, true_range_sixty_day_average_amount, efficiency_r60_ratio, efficiency_tr60_ratio, volume_sixty_day_average_count FROM i WHERE trading_symbol_code = 'AAPL' ORDER BY price_date DESC LIMIT 2",
    }
    for name, sql in checks.items():
        print(f"== {name}\n{run(args.profile, args.warehouse, sql)}")


if __name__ == "__main__":
    main()
