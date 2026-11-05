## Context

- `silver_domain_investments.price_daily` holds the eight commodity benchmarks (`^TRCCRB` from 1994, `^SPGSCI`
  from 1984, `GC=F`, `SI=F`, `HG=F`, `CL=F` from 2000, `DBC`, `GSG` from 2006) in prd; dev has one year
  (they were added after dev's full load). `price_indicator_daily` gives every listing a 200-row average of the
  adjusted close and a 20-row slope ratio.
- `market_rate_daily` holds `us_cpi_all_items_not_seasonally_adjusted` carried forward to every weekday from the
  first day of its month (`is_carried_forward`), and `us_federal_funds_effective_rate` (FRED DFF) on every
  calendar day.
- `monitor_daily_signal` is long (one row per day, monitor, lens, signal); market climate writes its rows from
  `common/market_climate_signals_sql.py`. Its columns fit another monitor: `is_yes`, `band_code`,
  `measured_value`, `threshold_value`, `reason_text`, `yes_count`, `action_name`.
- The dashboard and the Genie agent are generated from `src/common` builders (`cicd/build_market_climate.py`).

## Goals / Non-Goals

**Goals:** the four stars and the rating per trading day as far back as the inputs allow (1994 with the CRB);
every figure behind a star traceable to a silver row; the rating, its drilldown and the real rate on a dashboard
and in the Genie agent; dev with the same history as prd.

**Non-Goals:** a CPI release lag; other countries' rates and CPI; a combined commodity index of our own;
trading signals or shortlists from the rating.

## Decisions

### D1. Dev reload before anything else
`run_yahoo` with `reload_symbols=^TRCCRB,^SPGSCI,GC=F,SI=F,HG=F,CL=F,DBC,GSG` as the CI principal
(`cicd/run_dev.py yahoo --param reload_symbols=...`), then `run_investments`. Pass: first dates in dev equal prd's
(probe P1).

Finding: `reload_symbols` alone reloaded from the symbol's first stored day, which in dev was already
2025-11-03, so the first run changed nothing. `plan()` in `common/yahoo_market.py` now loads all history Yahoo has for
a benchmark named in `reload_symbols` (a new benchmark already did).

### D2. Commodities: the CRB votes
The 2004 plan used the old CRB (17 commodities, equal weights). In 2005 the index was rebuilt with uneven weights
(energy about 39%); that is the `^TRCCRB` series loaded. The old equal-weighted formula continues as the
Continuous Commodity Index (CCI), and the Bloomberg Commodity Index (BCOM) is the most diversified of the
large indexes, but neither is a free daily series in our sources today; `^SPGSCI` is about 60% energy, so it
tracks oil more than commodities. So the CRB votes, as the user chose; the other seven are context. Adding CCI
or BCOM later is one row in `data/portfolio/benchmarks.csv` if a source is found.

### D3. `market_rate_indicator_daily` (silver, materialized view)
One row per `rate_code` and `indicator_date`, where the dates are the `^GSPC` price dates (trading days, so
"200 days" means the same as for prices). `rate_value` is the latest value of the series on or before the date.
Series (`unit_name` percent, except the CPI index in index points):

| `rate_code` | Value |
|---|---|
| `us_cpi_all_items_not_seasonally_adjusted` | the CPI index (index points), carried from its reading to every date |
| `us_federal_funds_effective_rate` | DFF as reported |
| `us_cpi_change_previous_reading_percent` | CPI (not seasonally adjusted) over the previous month's CPI, minus 1, x 100; it changes once a month and is carried |
| `us_cpi_change_twelve_months_percent` | CPI over the CPI 12 months earlier, minus 1, x 100 |
| `us_real_federal_funds_rate` | the effective rate minus the CPI change over 12 months |

Columns: `rate_code`, `rate_name`, `indicator_date`, `rate_value` (DECIMAL(18,6)), `two_hundred_day_average_value`
(the average of the last 200 rows, empty when fewer), `two_hundred_day_average_change_value` (that average minus
the same average 20 rows earlier, in the series' units; a difference, not a ratio, because a change in percent
can be zero or negative), `day_count`, `is_calculated` (true for the three series we derive), `unit_name`,
`ingested_timestamp` (earliest input). The CPI changes are worked out on the monthly readings (rows with
`is_carried_forward` false) and then carried, as the story README decided. Twelve-month change rather than the
monthly one for the real rate, because the effective rate is a yearly rate. A day-over-day change of the carried
index is 0 on about 20 of 21 days and jumps on reading days, so the daily change kept is the change against the
previous reading, carried (user, 2026-11-05: index, 200-day average and change, all daily).

### D4. 52-week high and low on `price_indicator_daily`
`price_high_fifty_two_week_amount` = the highest `price_high` and `price_low_fifty_two_week_amount` = the lowest
`price_low` of the listing over price dates in the 364 days up to and including the row's date (a `RANGE`
window on the date), from the reported (not adjusted) prices, as finance sites show them. It sits with the other
calculated values, not in `price_daily`, because `price_daily` keeps reported values only (README decision). The
dashboard's `ds_company_figures` reads these columns; its 52-week figures for EQT must not change (P2).

### D5. The monitor's rows
`monitor_code` `inflation_deflation`, `monitor_name` "Inflation deflation", one lens `game_plan` ("Inflation/deflation
game plan"). Per trading day of `^GSPC`, an input counts when its latest row is at most 7 days old (CPI is
carried, the Fed series lags a few days; same rule as market climate's Fed answer). `is_yes` true means the star
is on (pointing to inflation):

| `signal_code` | Star on when | `measured_value` | `threshold_value` |
|---|---|---|---|
| `commodity_prices` | the CRB 200-day average slope ratio is above 0 | the slope ratio | 0 |
| `consumer_prices` | the 200-day average of the CPI index is higher than 20 rows earlier (the curve is going up) | the average's change in index points | 0 |
| `gold_prices` | the `GC=F` adjusted close is above its 200-day average | the close | the average |
| `interest_rates` | the effective rate is above its 200-day average | the rate | the average |

`band_code` on a star row: red when on, green when off. The rating row: `signal_code` `rating`, `yes_count` =
stars on (0 to 4), `measured_value` = the rating (-1 to 4; -1 when no star is on and the CPI 12-month change is
below 0), `threshold_value` = the CPI 12-month change, `action_name` = the label, `band_code` red (3 or 4),
yellow (2), green (0 or 1), blue (-1). A day without all four inputs has no rows for this monitor. The query is
`common/inflation_signals_sql.py` (plain strings, as market climate's), thresholds in `common/inflation.py`;
`monitor_daily_signal` becomes the union of both monitors. The column comments name the new values.

### D6. Dashboard "Inflation-Deflation Monitor"
Its own dashboard (each story its own, the agent spans them). Generic widget helpers move from
`common/market_climate_dashboard.py` to `common/dashboard_widgets.py` (no change to the Market Climate JSON).
New `common/inflation_queries.py` and `common/inflation_dashboard.py`; `cicd/build_market_climate.py` becomes
`cicd/build_dashboards.py` writing all three generated files. Pages:
- *Game plan*: bullet intro, the rating as of a date (a star row for the four vehicles, the label), the rating's
  history, one chart per star with its line (CRB with its 200-day average; CPI change and its average; gold with
  its average; the effective rate with its average), the real interest rate, the answers table, data dates.
- *Commodities*: the eight benchmarks, each against its 200-day average (context; only the CRB votes).
Same 36-month axis and colours as Market Climate.

### D7. Genie agent
Adds `market_rate_indicator_daily` and `price_indicator_daily`; instructions get the four stars, the rating and
labels, the short-term rate and the real rate; examples from the new dashboard's queries; three benchmarks
("How many inflation stars are on today?", "What is the real interest rate today?", "When was the last
deflation rating?"). Tables stay under the API limit of 30.

## Probes

- **P1**: dev reload; first price dates of the eight in dev equal prd.
- **P2**: the new indicator queries before deploy: the effective rate's 200-day average on a date equals a hand
  average of `market_rate_daily` over the last 200 `^GSPC` dates; EQT's 52-week high and low equal the dashboard's
  current figures (68.24, 47.94 on 2026-11-03).
- **P3**: the signal query over prd history before deploy: ratings per year; 2009 must show -1 days (US CPI was below
  its level of a year earlier from March to October 2009), 2021-2022 mostly 3 or 4. A surprise is explained before
  building on it.
- **P4**: every dashboard and Genie query runs in dev; the Genie benchmark evaluation passes; the user checks the
  dashboard and asks the agent.

## Risks / Trade-offs

- [CPI counts from the first day of its month, about six weeks before it is published] → kept, as decided for
  `market_rate_daily`; the rating can look ahead by up to six weeks. A release lag is a later change; the
  dashboard intro says so.
- [The CPI index rises in almost every period, so the consumer star is on most days] → intended: the model asks
  whether the curve goes up; the star goes off when CPI turns down (2009). The monthly change, not seasonally
  adjusted, is seasonal, so it is shown but does not vote; the 12-month change decides deflation and the real rate.
- [Quota 486 of 500 after this] → nothing else adds tables before a clean-up; recorded in the probe register.
- [The CRB series on Yahoo has gaps (248 rows a year in dev against 253)] → the 7-day rule covers short gaps.

## Migration Plan

Dev: reload (D1), draft PR deploys, `run_investments verify=true`. Prd: the merge deploys and CI runs `investments`.
Rollback: revert; the new table and its hidden copy are dropped by hand (user approval).
