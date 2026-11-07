"""Probe P8 (strategies, read only): is `revenue` ever the same figure as `net_income` in company_fundamentals (dev)?

Counts filings with a revenue, those where revenue equals net income, and where revenue is below net income, plus the
concept map of a few well known companies for a hand comparison with their filings.

Usage: uv run python -I references/poc/strategies/p8_revenue_vs_net_income.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inflation-deflation-monitor"))
from probe import run  # noqa: E402

S = "mdp_dev.silver_domain_investments"
print("filings with revenue, revenue = net income, revenue < net income, revenue < 0:")
print(run("DEFAULT", f"""SELECT count(revenue), count_if(revenue = net_income), count_if(revenue < net_income),
  count_if(revenue < 0) FROM {S}.company_fundamentals"""))
print("latest filing per well known company (symbol, revenue m, net income m, concepts):")
for row in run("DEFAULT", f"""SELECT l.trading_symbol_code, round(f.revenue / 1e6, 0), round(f.net_income / 1e6, 0),
  f.concept_used['revenue'], f.concept_used['net_income'], f.valid_from_date
  FROM {S}.company_fundamentals f JOIN {S}.listing l ON l.company_id = f.company_id
  WHERE l.trading_symbol_code IN ('AAPL', 'MSFT', 'NVDA', 'JPM', 'XOM', 'WMT')
  QUALIFY row_number() OVER (PARTITION BY l.trading_symbol_code ORDER BY f.valid_from_date DESC) = 1
  ORDER BY 1"""):
    print("  ", row)
