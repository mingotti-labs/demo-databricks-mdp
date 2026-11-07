"""Probe P4 (strategies, read only): the strategy-inputs figures in dev.

1. Share of current members with a revenue on the latest valuation day, and the concepts used.
2. One member's price-to-sales by hand from its filing revenue and price.
3. First and last price date of the five bear funds.
4. The index P/E of a day both environments have, dev (with the change) against prd (without it).

Usage: uv run python -I references/poc/strategies/p4_inputs_dev.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inflation-deflation-monitor"))
from probe import run  # noqa: E402

G = "mdp_dev.gold_analytics_gateway"
S = "mdp_dev.silver_domain_investments"
LATEST = f"(SELECT max(valuation_date) FROM {G}.valuation_daily_index_member)"

print("1. latest day, members, with revenue, with price_to_sales_ratio, used:")
print(run("DEFAULT", f"""SELECT valuation_date, count(*), count(revenue_trailing_twelve_months_amount),
  count(price_to_sales_ratio), count_if(is_used) FROM {G}.valuation_daily_index_member
  WHERE valuation_date = {LATEST} GROUP BY 1"""))
print("   concepts used for revenue on each member's latest filing:")
print(run("DEFAULT", f"""SELECT concept_used['revenue'] AS concept, count(*) FROM (
  SELECT concept_used, row_number() OVER (PARTITION BY company_id ORDER BY valid_from_date DESC) AS pick
  FROM {S}.company_fundamentals) WHERE pick = 1 GROUP BY 1 ORDER BY 2 DESC"""))

print("2. one member by hand (largest price-to-sales on the latest day):")
print(run("DEFAULT", f"""SELECT l.trading_symbol_code, m.price_close, m.share_count, m.market_value_amount,
  m.revenue_trailing_twelve_months_amount, m.price_to_sales_ratio,
  round(m.price_close * m.share_count / m.revenue_trailing_twelve_months_amount, 4) AS by_hand
  FROM {G}.valuation_daily_index_member m JOIN {S}.listing l USING (listing_id)
  WHERE m.valuation_date = {LATEST} AND m.price_to_sales_ratio IS NOT NULL
  ORDER BY m.price_to_sales_ratio DESC LIMIT 3"""))
print("   members above 15:", run("DEFAULT", f"SELECT count(*) FROM {G}.valuation_daily_index_member WHERE valuation_date = {LATEST} AND price_to_sales_ratio > 15"))

print("3. bear funds in price_daily:")
print(run("DEFAULT", f"""SELECT trading_symbol_code, min(price_date), max(price_date), count(*) FROM {S}.price_daily
  WHERE trading_symbol_code IN ('SQQQ','PSQ','SH','SDS','SPXU') GROUP BY 1 ORDER BY 1"""))

print("4. index P/E on 2026-10-30, dev then prd:")
for env in ("dev", "prd"):
    print("  ", env, run("DEFAULT", f"""SELECT members_used_count, price_earnings_trailing_twelve_months_ratio,
  price_earnings_ten_year_average_ratio, price_earnings_ten_year_average_inflation_adjusted_ratio
  FROM mdp_{env}.gold_analytics_gateway.valuation_daily_index WHERE valuation_date = DATE '2026-10-30'"""))
