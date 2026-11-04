"""Probe P2 (market-climate-gold, read only): run monitor_signal_query() on the SQL warehouse.

Prints row counts per signal and lens, the latest day's rows, the Fed hike windows, and checks every
result row's light against the yes count.

Usage: uv run python p2_signals_query.py --profile <PROFILE> [--catalog mdp_dev]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "references" / "poc" / "single-silver-landing-schema"))
from common.market_climate_signals_sql import monitor_signal_query  # noqa: E402
from common.market_climate_sql import DOMAIN, index_valuation_query  # noqa: E402
from compare import cli, sql  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog", default="mdp_dev")
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]

    def qualify(text: str) -> str:
        return text.replace(f"{DOMAIN}.", f"{args.catalog}.{DOMAIN}.")

    signals = qualify(monitor_signal_query(f"({index_valuation_query()})"))
    base = f"WITH s AS ({signals})"

    def run(title: str, statement: str) -> None:
        print(f"== {title}")
        for row in sql(args.profile, warehouse, f"{base} {statement}"):
            print("  ", " | ".join(str(x) for x in row))

    run("rows per lens and signal: first date, last date, rows",
        "SELECT lens_code, signal_code, min(signal_date), max(signal_date), count(*) FROM s GROUP BY 1, 2 ORDER BY 1, 2")
    run("latest day, every row (lens, signal, yes, band, measured, threshold, yes_count, action)",
        "SELECT lens_code, signal_code, is_yes, band_code, measured_value, threshold_value, yes_count, action_name "
        "FROM s WHERE signal_date = (SELECT max(signal_date) FROM s WHERE signal_code = 'climate') ORDER BY 1, 2")
    run("reason texts of the latest day (long run)",
        "SELECT signal_code, reason_text FROM s WHERE lens_code = 'long_run' "
        "AND signal_date = (SELECT max(signal_date) FROM s WHERE signal_code = 'climate') ORDER BY 1")
    run("climate rows whose light does not follow the yes count (must be empty)",
        "SELECT signal_date, lens_code, yes_count, band_code FROM s WHERE signal_code = 'climate' AND "
        "band_code != CASE yes_count WHEN 0 THEN 'green' WHEN 1 THEN 'yellow' ELSE 'red' END LIMIT 5")
    run("climate rows whose yes count differs from the answers (must be empty)",
        "SELECT c.signal_date, c.lens_code FROM s c JOIN (SELECT signal_date, lens_code, count_if(is_yes) AS n FROM s "
        "WHERE signal_code != 'climate' GROUP BY 1, 2) a ON a.signal_date = c.signal_date AND a.lens_code = c.lens_code "
        "WHERE c.signal_code = 'climate' AND c.yes_count != a.n LIMIT 5")
    run("Fed answers: days in the way per year (long run lens)",
        "SELECT year(signal_date), count_if(is_yes), count(*) FROM s WHERE signal_code = 'fed_in_the_way' "
        "AND lens_code = 'long_run' GROUP BY 1 ORDER BY 1")
    run("Fed: first and last day of the 2022-2023 hike run (is_yes)",
        "SELECT min(signal_date), max(signal_date) FROM s WHERE signal_code = 'fed_in_the_way' AND lens_code = 'long_run' "
        "AND is_yes AND signal_date BETWEEN DATE '2022-03-01' AND DATE '2024-06-30'")


if __name__ == "__main__":
    main()
