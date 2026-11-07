## Why

The Company Deep Dive (a company's price with Bollinger bands, last close, 52-week range and the steps behind its P/E) lived
only in the Market Climate dashboard. The user, looking at companies in the Strategy Monitor (short selling candidates) and
the other monitors, wants it in each of them. Started as a spike (planning discussion 2026-11-07): drill-through to the page was
checked and does not fit, because Databricks fills only filters on a dataset the source and target pages share, our page selects
by a parameter and every table has its own dataset; a link column to a separate dashboard needs the target's id per environment
and an undocumented URL syntax (the user chose not to probe it). So each dashboard gets the same page and its own company
dropdown.

## What Changes

- The page, its price chart, its datasets and parameters move from `src/common/market_climate_dashboard.py` into one module,
  `src/common/company_page.py`; every generated dashboard adds `company_page()`, the datasets of `company_datasets()`, the
  parameters of `company_parameters(dataset)` and drives the date-bound datasets (`DATE_BOUND`) with its own as-of date filter.
- Dashboards with the page: Market Climate Monitor (unchanged output), Inflation-Deflation Monitor, Currency Monitor and
  Strategy Monitor (page "Company Deep Dive", the same widgets and queries in each).
- No click-through from tables to the page: the company is picked in the page's dropdown (a click-through is possible only through
  a table link action whose URL needs the target dashboard's id per environment; not built).

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `gold-market-climate`: the Company Deep Dive page also appears in the other monitor dashboards.

## Impact

- Table slots: none. Quota 488 of 500.
- Dashboards only: the deploy publishes the changed dashboards; no unit runs and no data change. The Market Climate dashboard file
  and the Genie agent file are byte-identical to before.
- Not in this change: links from tables to the page, drill-through.

## Cross-repo dependencies

None. Stacked on `strategy-monitor-dashboard` (PR #192): the Strategy Monitor gets the page here, and all pull requests deploy to
one shared dev bundle, so a branch without that dashboard would plan to delete it (CI cannot confirm deletes). Merge #192 first.

## Model

Sonnet: a move of existing code into a shared module and four builder lines, verified by byte-identical output.
