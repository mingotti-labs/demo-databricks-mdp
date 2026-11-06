"""Probe P1 (strategies, read only): strategy 001 (bear market mutual fund) on prd data, week by week.

Week close = the last S&P 500 (^GSPC) close of each Monday-based week. Setup = any market climate light red on that
day and the close lower than five week closes earlier. Entry = setup on and the week's change at most -2.5%.
Interim = setup on, the week's change between 0 and -2.5%, and a close on Monday to Wednesday of the next week at
least 2.5% below that week close.

Usage: uv run python -I references/poc/strategies/p1_bear_fund_weeks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inflation-deflation-monitor"))
from probe import run  # noqa: E402

G = "mdp_prd.gold_analytics_gateway"
S = "mdp_prd.silver_domain_investments"
WEEKS = f"""
WITH days AS (SELECT price_date, price_close FROM {S}.price_daily WHERE trading_symbol_code = '^GSPC'),
weeks AS (SELECT date_trunc('WEEK', price_date) AS week_start, max(price_date) AS week_end_date,
  max_by(price_close, price_date) AS week_close FROM days GROUP BY 1),
w AS (SELECT *, lag(week_close, 1) OVER (ORDER BY week_start) AS previous_close,
  lag(week_close, 5) OVER (ORDER BY week_start) AS five_weeks_close FROM weeks),
red AS (SELECT signal_date, max(CAST(band_code = 'red' AS INT)) = 1 AS is_any_red
  FROM {G}.monitor_daily_signal WHERE monitor_code = 'market_climate' AND signal_code = 'climate' GROUP BY 1),
s AS (SELECT w.*, r.is_any_red, w.week_close < w.five_weeks_close AS is_lower_than_five_weeks,
  w.week_close / w.previous_close - 1 AS week_change_ratio
  FROM w JOIN red r ON r.signal_date = w.week_end_date)
"""

print("Weeks with a climate row, setup on, entries by band:")
print(run("DEFAULT", WEEKS + """
SELECT count(*) AS weeks, count_if(is_any_red) AS red_weeks,
  count_if(is_any_red AND is_lower_than_five_weeks) AS setup_weeks,
  count_if(is_any_red AND is_lower_than_five_weeks AND week_change_ratio <= -0.05) AS entry_50,
  count_if(is_any_red AND is_lower_than_five_weeks AND week_change_ratio <= -0.025 AND week_change_ratio > -0.05) AS entry_25,
  count_if(is_any_red AND is_lower_than_five_weeks AND week_change_ratio < 0 AND week_change_ratio > -0.025) AS watch_weeks
FROM s"""))

print("Setup weeks, one row each:")
for row in run("DEFAULT", WEEKS + """
SELECT week_end_date, round(week_close, 2), round(five_weeks_close, 2), round(week_change_ratio * 100, 2)
FROM s WHERE is_any_red AND is_lower_than_five_weeks ORDER BY week_end_date"""):
    print("  ", row)

print("Interim entries (Mon-Wed close at least 2.5% below the watch week's close):")
print(run("DEFAULT", WEEKS + f"""
SELECT s.week_end_date, d.price_date, round(d.price_close / s.week_close - 1, 4)
FROM s JOIN {S}.price_daily d ON d.trading_symbol_code = '^GSPC'
  AND d.price_date > s.week_end_date AND d.price_date <= date_add(s.week_end_date, 5)
  AND dayofweek(d.price_date) IN (2, 3, 4)
WHERE s.is_any_red AND s.is_lower_than_five_weeks AND s.week_change_ratio < 0 AND s.week_change_ratio > -0.025
  AND d.price_close / s.week_close - 1 <= -0.025
ORDER BY 2"""))
