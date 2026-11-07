## Why

Two asks from the user, packaged together on 2026-11-07 because both are small and add no table:

1. **US yields in the Yield Deep Dive.** The Currency Monitor's Yield Deep Dive ranks countries by their short-term rate,
   but the user wants to see the 10-year US Treasury yield against shorter US yields (3 months, 1, 2 and 3 years; one or
   several at once), to read the shape of the curve. We load only the 10-year (`DGS10`). FRED publishes every US Treasury
   maturity daily (`DGS3MO`, `DGS1`, `DGS2`, `DGS3`, probe P1 of `references/poc/us-yields/`). For the other countries
   FRED has only a monthly 3-month and 10-year rate, so this part is US only. The Currency Monitor does not need the
   Company Deep Dive page (user, 2026-11-07); it leaves that dashboard.
2. **Strategy 004 (Trading Efficient Stocks) indicators.** The story's acceptance criteria: the 60-day rate of change,
   the daily range and its 60-day simple average, the true range and its 60-day simple average, and two efficiency
   ratios, *ar* = 60-day rate of change / 60-day average range and *atr* = 60-day rate of change / 60-day average true
   range; the screening also needs the 60-day average volume. The screening rules (efficiency of 15 or more, a smooth
   rise) and the setup, entry and exit come later.

## What Changes

- FRED fetch: four more series, `DGS3MO`, `DGS1`, `DGS2`, `DGS3` (the run loads their full history the first time).
- `silver_domain_investments.market_rate_daily`: four more daily rates, `us_3_month_treasury_yield`,
  `us_1_year_treasury_yield`, `us_2_year_treasury_yield`, `us_3_year_treasury_yield`.
- Currency Monitor, page Yield Deep Dive: a chart of the US 10-year yield against the short-term US yields the user picks
  (one or several of 3 months, 1, 2 and 3 years) over the history range of the other charts; the Company Deep Dive page
  is removed from the Currency Monitor (it stays in the other three dashboards). The Genie agent gets the chart's query
  as an example, like every dashboard query.
- `silver_domain_investments.price_indicator_daily`: new columns for strategy 004, each with a Unity Catalog description:
  the 60-day change, the day's range and true range, each in dollars and as a fraction of the close, their 60-day
  averages, the two efficiency ratios (dollars over dollars: the 60-day change over the 60-day average range or true
  range) and the 60-day average volume.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fred-rates-ingestion`: four more US Treasury series.
- `silver-domain-investments`: four more market rates; the strategy 004 columns of `price_indicator_daily`.
- `gold-currency-monitor`: the Yield Deep Dive also plots the US 10-year against chosen short-term US yields.
- `gold-market-climate`: the Company Deep Dive page is in the Inflation-Deflation and Strategy dashboards, not the
  Currency Monitor.

## Impact

- Table slots: none (new rows and columns in existing tables). Quota 488 of 500.
- Units: `fred` (new series, full history once) then `investments` (silver and gold); CI runs them alphabetically, which
  is the right order. `price_indicator_daily` is a materialized view, recomputed in full on every run.
- Dashboards: Currency Monitor (new chart, one page fewer); the Genie agent file (one more example).
- Not in this change: the strategy 004 screening, setup, entry and exit rules and a dashboard for them; short and long
  yields of other countries.

## Cross-repo dependencies

None.

## Model

Sonnet: four series in an existing list, columns on an existing view and one chart in an existing dashboard, all on
established patterns; the units of the efficiency ratio were settled by the user.
