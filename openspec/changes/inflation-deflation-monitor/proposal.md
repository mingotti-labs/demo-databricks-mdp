## Why

Story 2 of the agreed order (planning `references/user-stories/monitor-inflation-deflation-game-plan.md`): the
individual investor wants to know whether the game is inflationary or deflationary, from four vehicles
(commodity prices, consumer prices, gold, interest rates), each giving a star, summed into a rating from
minus one (deflation) to four (increasing inflation). Most inputs are already in silver: the eight commodity
benchmarks with their 200-day averages (full history in prd, one year in dev), US CPI carried to every
weekday, and the federal funds effective rate every day. What is missing is a 200-day average on the rates
and on CPI's change, the rule, and a place to see it. The user's 2004 game plan uses the CRB index, the
short-term interest rate and CPI; the user also asked for the real interest rate (short-term rate minus CPI
inflation) as a daily series, and for the 52-week high and low noted on 2026-11-05.

## What Changes

- **Dev data first**: the eight commodity benchmarks reloaded in full in dev (`run_yahoo reload_symbols=...`, then
  `run_investments`), so dev has the same history as prd.
- **New silver `market_rate_indicator_daily`**: one row per series and trading day (the `^GSPC` price dates),
  with the series value (latest on or before the day), its 200-day average, and the change of that average over
  20 rows. Five series: the CPI index itself (`us_cpi_all_items_not_seasonally_adjusted`, carried to every day),
  the CPI change against the previous reading (carried until the next one), the CPI change over 12 months,
  `us_federal_funds_effective_rate` (the short-term rate) and `us_real_federal_funds_rate` (the short-term rate
  minus the CPI 12-month change); the changes and rates in percent.
- **52-week high and low** on `price_indicator_daily` (`price_high_fifty_two_week_amount`,
  `price_low_fifty_two_week_amount`), for every listing and day. The dashboard's Company Deep Dive reads them
  instead of working them out.
- **The monitor** as rows of the existing gold `monitor_daily_signal` (monitor `inflation_deflation`, one lens
  `game_plan`), no new gold table: four star rows (commodity prices: the CRB 200-day average rising; consumer
  prices: the 200-day average of the CPI index rising; gold: the gold price above its 200-day average; interest
  rates: the short-term rate above its 200-day average) and a rating row (stars 0 to 4, or minus one when no
  star is on and CPI over 12 months is below zero), with its label (Increasing Inflation, Inflation Danger, Some
  Inflation Risk, Mild or Decreasing Inflation, Decreasing Inflation, Deflation) and a plain reason.
- **Dashboard "Inflation-Deflation Monitor"** (the Market Climate dashboard is renamed "Market Climate Monitor") (its own dashboard, built by the same pattern as Market Climate): the
  rating as of a date and its four stars, the rating's history, a chart per star with its line, the real
  interest rate, and the other seven commodity benchmarks against their averages for context.
- **The Genie agent** (title "Market Climate", provisional) gains the new tables, the inflation rules in its
  instructions, examples from the new dashboard's queries and benchmark questions.
- **Verification**: the gold verification checks the new monitor's rows (five per day, the rating equals its
  stars, minus one only with CPI below zero over 12 months).

## Decisions (user, 2026-11-05)

- Interest rates: the **short-term** rate, the US federal funds effective rate (already daily). The 10-year
  yield is the long-term rate and does not vote.
- Real interest rate: the short-term rate minus CPI inflation, as a daily series (shown, does not vote).
- Commodities: the CRB index votes; the other seven benchmarks are shown for context. There is no clearly
  better free daily series (design D2 explains why).
- Deflation (minus one): all four stars off and CPI below zero.
- CPI (user, 2026-11-05): daily series of the index, its 200-day average and its change; the model tracks the
  trajectory of the curve, so the consumer star is the slope of the index's 200-day average, the same rule as
  commodities. Daily granularity, a monthly reading carried forward.

## Capabilities

### New Capabilities
- `gold-inflation-deflation`: the inflation/deflation monitor rows, its dashboard and its part of the Genie agent.

### Modified Capabilities
- `silver-domain-investments`: `market_rate_indicator_daily` (new) and the 52-week high and low on price indicators.

## Impact

- Table slots: +2 per environment (one materialized view and its hidden copy) = +4. Now 482 (quota API,
  2026-11-05): 486 after, under the 488 stop line. Nothing else may add tables until a clean-up.
- `price_indicator_daily` gains two columns; its rows and other columns do not change. `monitor_daily_signal`
  gains rows (about 5 per trading day since 1994), its columns and the market climate rows do not change.
- Runs: silver and gold code change, so CI runs `investments` (silver then gold). Dev needs the Yahoo reload
  first (one run of `run_yahoo` with `reload_symbols`).
- Not in this change: a release lag for CPI (today CPI counts from the first day of its month, before it is
  published; design Risks); tagging (next change); a semantic layer.

## Cross-repo dependencies

None. The CI principal already writes `silver_domain_investments` and `gold_analytics_gateway`, and can redeploy
dashboards and Genie agents (iac `cicd-sp-sql-access`).
Planning repo: the story gets a short Analysis section (rules as decided, sources) at archive.

## Model

Sonnet for implementation: the rules and tables are settled here and each part follows an existing pattern
(price indicators, the market climate signals, the dashboard and Genie builders).
