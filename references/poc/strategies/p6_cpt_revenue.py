"""Probe P6 (strategies, read only): why does Camden Property Trust (CPT) get a revenue of 14.9 million in dev?

Lists CPT's revenue facts of the 10-Q filed 2026-11-06 and of its 10-K filed 2026-02-12, per mapped concept.

Usage: uv run python -I references/poc/strategies/p6_cpt_revenue.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inflation-deflation-monitor"))
from probe import run  # noqa: E402

L = "mdp_dev.silver_landing.sec__company_facts"
for filed in ("2026-11-06", "2026-02-12"):
    print("facts of the filing dated", filed)
    for row in run("DEFAULT", f"""SELECT concept, form, start, `end`, val FROM {L}
      WHERE entity_name LIKE 'CAMDEN PROPERTY%' AND is_current AND filed = DATE '{filed}'
        AND concept IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'RevenuesNetOfInterestExpense')
      ORDER BY concept, `end`, start"""):
        print("  ", row)

G = "mdp_dev.gold_analytics_gateway"
S = "mdp_dev.silver_domain_investments"
LATEST = f"(SELECT max(valuation_date) FROM {G}.valuation_daily_index_member)"
print("members above 15 on the latest day: symbol, price_to_sales, revenue (m), net income (m), concept")
for row in run("DEFAULT", f"""SELECT l.trading_symbol_code, m.price_to_sales_ratio,
  round(m.revenue_trailing_twelve_months_amount / 1e6, 1), round(m.earnings_trailing_twelve_months_amount / 1e6, 1),
  f.concept_used['revenue']
  FROM {G}.valuation_daily_index_member m JOIN {S}.listing l USING (listing_id)
  JOIN {S}.company_fundamentals f ON f.company_id = m.company_id AND f.valid_from_date = m.filing_valid_from_date
  WHERE m.valuation_date = {LATEST} AND m.price_to_sales_ratio > 15 ORDER BY 2 DESC"""):
    print("  ", row)
print("members whose revenue is below their net income (impossible for a normal company):")
for row in run("DEFAULT", f"""SELECT l.trading_symbol_code, round(m.revenue_trailing_twelve_months_amount / 1e6, 1),
  round(m.earnings_trailing_twelve_months_amount / 1e6, 1), f.concept_used['revenue']
  FROM {G}.valuation_daily_index_member m JOIN {S}.listing l USING (listing_id)
  JOIN {S}.company_fundamentals f ON f.company_id = m.company_id AND f.valid_from_date = m.filing_valid_from_date
  WHERE m.valuation_date = {LATEST} AND m.revenue_trailing_twelve_months_amount < m.earnings_trailing_twelve_months_amount
  ORDER BY 1"""):
    print("  ", row)
