"""Probe P18 (strategies, read only): why did NVDA give no short-selling signal on the week to 2026-11-13?

Prints NVDA's weekly states from the exact states query, the climate rows of that week, and NVDA's member row and
weekly closes, so each part of the setup (red, price-to-sales, weeks down) can be checked on its own.

Usage: uv run python -I references/poc/strategies/p18_nvda_short_gate.py [dev|prd]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inflation-deflation-monitor"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from probe import run  # noqa: E402

from common.strategy_events_sql import strategy_states_query  # noqa: E402

env = sys.argv[1] if len(sys.argv) > 1 else "dev"
gold = f"mdp_{env}.gold_analytics_gateway"
domain = f"mdp_{env}.silver_domain_investments"
STATES = strategy_states_query(domain=domain, climate_source=f"{gold}.monitor_daily_signal",
                               member_source=f"{gold}.valuation_daily_index_member")


def show(title: str, sql: str) -> None:
    print(title)
    for row in run("DEFAULT", sql):
        print("  ", row)


show("NVDA states from 2026-09-01:", f"SELECT week_start, week_end_date, week_close_amount, week_change_ratio, "
     f"price_to_sales_ratio, down_week_count, is_red, is_setup_on FROM ({STATES}) "
     f"WHERE strategy_code = 'short_selling' AND trading_symbol_code = 'NVDA' AND week_start >= '2026-09-01' ORDER BY week_start")
show("climate rows 2026-11-06 to 2026-11-20:", f"SELECT signal_date, lens_code, band_code FROM {gold}.monitor_daily_signal "
     f"WHERE monitor_code = 'market_climate' AND signal_code = 'climate' AND signal_date BETWEEN '2026-11-06' AND '2026-11-20' "
     f"ORDER BY signal_date, lens_code")
show("NVDA member rows from 2026-11-06:", f"SELECT valuation_date, price_to_sales_ratio FROM {gold}.valuation_daily_index_member m "
     f"JOIN {domain}.listing l ON l.listing_id = m.listing_id WHERE l.trading_symbol_code = 'NVDA' "
     f"AND valuation_date >= '2026-11-06' ORDER BY valuation_date")
show("NVDA daily closes from 2026-09-25 (adjusted, reported):", f"SELECT price_date, price_close_adjusted, price_close "
     f"FROM {domain}.price_daily WHERE trading_symbol_code = 'NVDA' AND price_date >= '2026-09-25' "
     f"AND dayofweek(price_date) = 6 ORDER BY price_date")
show("^GSPC days 2026-11-09 to 2026-11-20:", f"SELECT price_date FROM {domain}.price_daily WHERE trading_symbol_code = '^GSPC' "
     f"AND price_date BETWEEN '2026-11-09' AND '2026-11-20' ORDER BY price_date")
