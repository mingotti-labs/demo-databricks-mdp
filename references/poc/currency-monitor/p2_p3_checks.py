"""Probes P2 and P3 of currency-monitor (read only), on the tables built in dev.

P2: a cross rate against a hand calculation from the raw FRED rates; the inflation series equal prd's (the old query)
    after rounding to 6 decimals.
P3: the share of days the dollar is strong, per year (DXY and the broad index).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inflation-deflation-monitor"))
from probe import run  # noqa: E402

D = "mdp_dev.silver_domain_investments"
print("P2a. CHF in AUD on 2026-10-30: table, then by hand from the raw rates")
print("  table:", run("DEFAULT", f"SELECT rate_value, observation_date FROM {D}.market_rate_indicator_daily WHERE rate_code = 'currency_value_chf_in_aud' AND indicator_date = DATE '2026-10-30'"))
print("  hand: ", run("DEFAULT", f"""SELECT (1 / c.rate_value) / a.rate_value FROM {D}.market_rate_daily c, {D}.market_rate_daily a
  WHERE c.rate_code = 'swiss_francs_per_us_dollar' AND a.rate_code = 'us_dollars_per_australian_dollar'
    AND c.observation_date = DATE '2026-10-30' AND a.observation_date = DATE '2026-10-30'"""))
print("P2b. series in the table:", run("DEFAULT", f"SELECT count(DISTINCT rate_code), count(*) FROM {D}.market_rate_indicator_daily"))
print("P2c. inflation series dev (new query) against prd (old query), rows that differ after rounding to 6 decimals:")
print("  ", run("DEFAULT", """SELECT count(*) FROM (
  SELECT rate_code, indicator_date, round(rate_value, 6) v, round(two_hundred_day_average_value, 6) a
  FROM mdp_dev.silver_domain_investments.market_rate_indicator_daily
  WHERE rate_code IN ('us_cpi_all_items_not_seasonally_adjusted','us_federal_funds_effective_rate','us_cpi_change_previous_reading_percent','us_cpi_change_twelve_months_percent','us_real_federal_funds_rate')
    AND indicator_date <= DATE '2026-11-02'
  EXCEPT
  SELECT rate_code, indicator_date, round(rate_value, 6), round(two_hundred_day_average_value, 6)
  FROM mdp_prd.silver_domain_investments.market_rate_indicator_daily)"""))
print("P3. dollar strong, days and share per year (DXY, broad index)")
for row in run("DEFAULT", """SELECT year(signal_date) y,
  count_if(signal_code = 'dollar_index') dxy_days, round(avg(CASE WHEN signal_code = 'dollar_index' THEN CAST(is_yes AS INT) END), 2) dxy_strong,
  count_if(signal_code = 'dollar_broad_index') broad_days, round(avg(CASE WHEN signal_code = 'dollar_broad_index' THEN CAST(is_yes AS INT) END), 2) broad_strong
FROM mdp_dev.gold_analytics_gateway.monitor_daily_signal
WHERE monitor_code = 'currency' AND signal_code IN ('dollar_index', 'dollar_broad_index') AND signal_date >= DATE '2005-01-01'
GROUP BY 1 ORDER BY 1"""):
    print("  ", row)
print("P3b. rows per currency series, first and last day:")
for row in run("DEFAULT", "SELECT signal_code, count(*), min(signal_date), max(signal_date) FROM mdp_dev.gold_analytics_gateway.monitor_daily_signal WHERE monitor_code='currency' AND lens_code='australian_dollar' GROUP BY 1 ORDER BY 1"):
    print("  ", row)
