"""Probe P11 (strategies, read only): strategy 002 when the setup also needs N straight weeks down (N = 3, 4, 5).

Story 002 changed on 2026-11-07: the setup also needs a down streak (3 weeks as written). Runs the strategy events query of
`strategy-events` with `down_week_count >= N` added to the short selling setup against the tables of one environment and
compares event counts, the entries, and the setups still open on the latest week with the query as built.

Usage: uv run python -I references/poc/strategies/p11_setup_three_weeks_preview.py [dev|prd]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inflation-deflation-monitor"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from probe import run  # noqa: E402

from common.strategy_events_sql import strategy_events_query  # noqa: E402

env = sys.argv[1] if len(sys.argv) > 1 else "prd"
AS_BUILT = strategy_events_query(
    domain=f"mdp_{env}.silver_domain_investments",
    climate_source=f"mdp_{env}.gold_analytics_gateway.monitor_daily_signal",
    member_source=f"mdp_{env}.gold_analytics_gateway.valuation_daily_index_member",
)
OLD = "r.is_red AND m.price_to_sales_ratio > 15 AS is_setup_on"
assert AS_BUILT.count(OLD) == 1


def variant(weeks: int) -> str:
    return AS_BUILT.replace(OLD, f"r.is_red AND m.price_to_sales_ratio > 15 AND s.down_weeks >= {weeks} AS is_setup_on")


print("as built (no streak in the setup): short_selling events, symbols")
print("  ", run("DEFAULT", f"SELECT event_code, count(*), count(DISTINCT trading_symbol_code) FROM ({AS_BUILT}) WHERE strategy_code = 'short_selling' GROUP BY 1 ORDER BY 1"))
for weeks in (3, 4, 5):
    query = variant(weeks)
    print(f"setup needs {weeks} weeks down: events, symbols")
    print("  ", run("DEFAULT", f"SELECT event_code, count(*), count(DISTINCT trading_symbol_code) FROM ({query}) WHERE strategy_code = 'short_selling' GROUP BY 1 ORDER BY 1"))
    print("   entries:")
    for row in run("DEFAULT", f"SELECT trading_symbol_code, event_date, setup_start_date, price_to_sales_ratio, down_week_count FROM ({query}) WHERE strategy_code = 'short_selling' AND event_code = 'entry' ORDER BY event_date"):
        print("     ", row)
    print("   setups open on the latest week:")
    for row in run("DEFAULT", f"""SELECT s.trading_symbol_code, s.setup_start_date, s.price_to_sales_ratio, s.down_week_count FROM ({query}) s
      WHERE s.strategy_code = 'short_selling' AND s.event_code = 'setup_start' AND NOT EXISTS (
        SELECT 1 FROM ({query}) e WHERE e.strategy_code = 'short_selling' AND e.trading_symbol_code = s.trading_symbol_code
          AND e.event_code = 'setup_end' AND e.setup_start_date = s.setup_start_date) ORDER BY 1"""):
        print("     ", row)
