"""Probe P3 (strategies, read only): how often do current S&P 500 members close six straight weeks down?

Week close = the last adjusted close of each Monday-based week. A week is down when its close is below the previous
week's close. The streak counts consecutive down weeks; an entry would fire the week a streak reaches 6. Counted on
weeks with a market climate row (from 2025-10-29), with and without a red light. Price-to-sales is left out: revenue
is not loaded yet.

Usage: uv run python -I references/poc/strategies/p3_six_weeks_down.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inflation-deflation-monitor"))
from probe import run  # noqa: E402

G = "mdp_prd.gold_analytics_gateway"
S = "mdp_prd.silver_domain_investments"
QUERY = f"""
WITH members AS (SELECT DISTINCT listing_id FROM {G}.valuation_daily_index_member
  WHERE valuation_date = (SELECT max(valuation_date) FROM {G}.valuation_daily_index_member)),
weeks AS (SELECT p.listing_id, date_trunc('WEEK', p.price_date) AS week_start, max(p.price_date) AS week_end_date,
  max_by(p.price_close_adjusted, p.price_date) AS week_close
  FROM {S}.price_daily p JOIN members m ON m.listing_id = p.listing_id
  WHERE p.price_date >= DATE '2025-06-01' GROUP BY 1, 2),
d AS (SELECT *, CAST(week_close < lag(week_close) OVER (PARTITION BY listing_id ORDER BY week_start) AS INT) AS is_down FROM weeks),
g AS (SELECT *, sum(1 - is_down) OVER (PARTITION BY listing_id ORDER BY week_start) AS run_group FROM d),
streak AS (SELECT *, sum(is_down) OVER (PARTITION BY listing_id, run_group ORDER BY week_start) AS down_weeks FROM g),
red AS (SELECT signal_date, max(CAST(band_code = 'red' AS INT)) = 1 AS is_any_red
  FROM {G}.monitor_daily_signal WHERE monitor_code = 'market_climate' AND signal_code = 'climate' GROUP BY 1)
SELECT count(DISTINCT s.listing_id) AS members, count_if(s.down_weeks = 6) AS reach_six,
  count_if(s.down_weeks = 6 AND r.is_any_red) AS reach_six_red, count(DISTINCT CASE WHEN s.down_weeks = 6 THEN s.listing_id END) AS members_reaching
FROM streak s JOIN red r ON r.signal_date = s.week_end_date
"""
print("members, weeks a streak reaches 6, of which red, members reaching 6:")
print(run("DEFAULT", QUERY))
