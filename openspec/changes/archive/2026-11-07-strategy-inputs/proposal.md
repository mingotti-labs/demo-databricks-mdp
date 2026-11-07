## Why

Strategies 001 (bear market mutual fund) and 002 (short selling), designed with the user on 2026-11-06 (planning
`docs/superpowers/specs/2026-11-06-strategies-001-002-design.md`, built in three changes). This is change 1 of 3: the
inputs the rules need and that the platform does not have yet. Strategy 002 screens stocks on price-to-sales above 15,
and no revenue figure is loaded (probe P2: SEC has it under several concepts). Strategy 001 buys a bear fund, and none
is loaded (probe P0: all five candidates have full Yahoo history).

## What Changes

- **Revenue**: figure `revenue` in `data/portfolio/concept_mapping.csv` (kind `duration`, so silver gives trailing
  twelve months like `net_income`), concepts in priority order `Revenues`,
  `RevenueFromContractWithCustomerExcludingAssessedTax`, `RevenuesNetOfInterestExpense`, `SalesRevenueNet`,
  `RevenueFromContractWithCustomerIncludingAssessedTax`. Silver `company_fundamentals` gets a `revenue` column with a
  Unity Catalog description. The SEC fetch keeps only mapped concepts, so the next `run_sec` writes a new facts file for
  every company (their content changes) and the history fills in by itself.
- **Price-to-sales**: gold `valuation_daily_index_member` gets `revenue_trailing_twelve_months_amount` (from the valid
  filing row) and `price_to_sales_ratio` (market value over that revenue, empty when either is missing or revenue is not
  above zero), both described.
- **Bear funds**: SQQQ, PSQ, SH, SDS, SPXU as rows of `data/portfolio/benchmarks.csv` (kind `bear_fund`), so Yahoo loads
  their full history and `price_daily` / `price_indicator_daily` carry them.
- Verification and pinned counts follow (`verification/bronze_checks/portfolio.yml`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `silver-domain-investments`: a revenue figure per filing.
- `gold-market-climate`: price-to-sales per index member and day.
- `portfolio-internal-data`: bear funds in the benchmarks.

## Impact

- Table slots: none (new columns and rows). Quota 484 of 500.
- Runs in prd after merge: `portfolio` (CSV changes), `sec` (refetches every company once, about 20 minutes), `yahoo`
  (five new symbols, full history), `investments` (silver and gold). CI runs units alphabetically
  (investments, portfolio, sec, yahoo): investments runs before the new data lands, so one more `run--investments--prd`
  by hand afterwards (as for currency-monitor).
- The index P/E and every existing column are unchanged (a new figure adds a column only).
- Not in this change: the strategy table (change 2, `strategy-events`), the dashboard and Genie (change 3).

## Cross-repo dependencies

None (no new schema, volume or secret). Planning: the design above; the story files are the rules.

## Model

Sonnet for implementation: a mapping row, a figure, two gold columns and CSV rows, each repeating an existing pattern.
