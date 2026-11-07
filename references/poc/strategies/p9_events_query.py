"""Probe P9 (strategies, read only): the strategy events query of `strategy-events` against dev (or prd) tables.

Runs the exact text of src/common/strategy_events_sql.py, counts the events per strategy and code and prints the
setup periods of strategy 001 and a sample of strategy 002.

Usage: uv run python -I references/poc/strategies/p9_events_query.py [dev|prd]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inflation-deflation-monitor"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from probe import run  # noqa: E402

from common.strategy_events_sql import strategy_events_query  # noqa: E402

env = sys.argv[1] if len(sys.argv) > 1 else "dev"
QUERY = strategy_events_query(
    domain=f"mdp_{env}.silver_domain_investments",
    climate_source=f"mdp_{env}.gold_analytics_gateway.monitor_daily_signal",
    member_source=f"mdp_{env}.gold_analytics_gateway.valuation_daily_index_member",
)
print("events per strategy and code:")
for row in run("DEFAULT", f"SELECT strategy_code, event_code, count(*), count(DISTINCT trading_symbol_code), min(event_date), max(event_date) FROM ({QUERY}) GROUP BY 1, 2 ORDER BY 1, 2"):
    print("  ", row)
print("key duplicates (expect 0):", run("DEFAULT", f"SELECT count(*) FROM (SELECT strategy_code, trading_symbol_code, event_date, event_code FROM ({QUERY}) GROUP BY 1, 2, 3, 4 HAVING count(*) > 1)"))
print("strategy 001 events:")
for row in run("DEFAULT", f"SELECT event_date, event_code, setup_start_date, entry_number, entry_band_code, week_change_ratio FROM ({QUERY}) WHERE strategy_code = 'bear_market_fund' ORDER BY event_date"):
    print("  ", row)
print("strategy 002 events (first 12 by date):")
for row in run("DEFAULT", f"SELECT trading_symbol_code, event_date, event_code, setup_start_date, entry_number, price_to_sales_ratio, down_week_count FROM ({QUERY}) WHERE strategy_code = 'short_selling' ORDER BY event_date, trading_symbol_code LIMIT 12"):
    print("  ", row)
print("a reason text per kind:")
for row in run("DEFAULT", f"SELECT DISTINCT strategy_code, event_code, reason_text FROM ({QUERY}) QUALIFY row_number() OVER (PARTITION BY strategy_code, event_code ORDER BY event_date) = 1"):
    print("  ", row)
