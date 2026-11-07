"""Probe P13 (strategies, read only): the events query after splitting out the weekly states gives the same rows as before.

Runs the events query frozen in p13_events_sql_before_split.py and the current one on the same tables and counts the rows
that are in one but not the other (EXCEPT both ways; expect 0 and 0), plus the row counts.

Usage: uv run python -I references/poc/strategies/p13_events_split_identical.py [dev|prd]
"""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "inflation-deflation-monitor"))
sys.path.insert(0, str(HERE.parents[2] / "src"))
from probe import run  # noqa: E402

from common.strategy_events_sql import strategy_events_query as after  # noqa: E402

spec = importlib.util.spec_from_file_location("events_before", HERE / "p13_events_sql_before_split.py")
before_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(before_module)

env = sys.argv[1] if len(sys.argv) > 1 else "dev"
args = dict(
    domain=f"mdp_{env}.silver_domain_investments",
    climate_source=f"mdp_{env}.gold_analytics_gateway.monitor_daily_signal",
    member_source=f"mdp_{env}.gold_analytics_gateway.valuation_daily_index_member",
)
BEFORE, AFTER = before_module.strategy_events_query(**args), after(**args)
print("rows before, after:", run("DEFAULT", f"SELECT (SELECT count(*) FROM ({BEFORE})), (SELECT count(*) FROM ({AFTER}))"))
print("in before, not in after:", run("DEFAULT", f"SELECT count(*) FROM (SELECT * FROM ({BEFORE}) EXCEPT SELECT * FROM ({AFTER}))"))
print("in after, not in before:", run("DEFAULT", f"SELECT count(*) FROM (SELECT * FROM ({AFTER}) EXCEPT SELECT * FROM ({BEFORE}))"))
