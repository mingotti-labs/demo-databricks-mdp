## Context

- FRED series come from `SERIES` in `src/common/fred_series.py`; a series with no stored rows loads its full history.
  `market_rate_daily` takes its rates from `RATES` (`src/common/investments.py`) plus `CURRENCY_RATES`;
  `verify_silver_domain_investments.py` checks every code of `RATES` has rows.
- The Currency Monitor's Yield Deep Dive (`currency_dashboard.yield_page`) ranks countries by short-term rate plus the
  12-month currency change. Charts over time use the `history_range_code` parameter and `with_range_dates` (Market Climate,
  Strategy Monitor). Every dashboard query is also a Genie example (`market_climate_genie.QUERIES`), with its parameters
  given literal values in `LITERALS`.
- `price_indicator_daily` (materialized view, one row per listing and price date) holds the 200-day average and the 52-week
  high and low. `price_daily` has the reported open, high, low and close, the adjusted close and the volume.

## Goals / Non-Goals

**Goals:** the US 10-year against chosen short-term US yields on the Yield Deep Dive; the strategy 004 indicators per
listing and day; the Currency Monitor without the Company Deep Dive.

**Non-Goals:** the strategy 004 screening, setup, entry and exit rules, a table or page for its candidates, Genie
questions on it (the indicators are silver; a gold strategy table comes with the rules); short and medium yields of
other countries (FRED has only monthly 3-month and 10-year rates for them); a yield-curve recession signal.

## Decisions

### D1. Four US Treasury series, daily, constant maturity

`DGS3MO`, `DGS1`, `DGS2`, `DGS3` join `SERIES` and `RATES` as `us_3_month_treasury_yield`, `us_1_year_treasury_yield`,
`us_2_year_treasury_yield`, `us_3_year_treasury_yield` (percent), the same family as `DGS10` (probe P1 of
`references/poc/us-yields/`: all daily, current to 2026-11-05; `DGS3MO` from 1981, `DGS2` from 1976, `DGS1` and `DGS3`
from 1962). Not `DGS1MO`, `DGS6MO`, `DGS5`, `DGS30`: the user named 3 months, 1, 2 and 3 years; adding one later is a
line in each list.

### D2. The chart: one row per date and short-term maturity, the 10-year on every row

Dataset `ds_us_yield_curve` returns, per trading date in the chosen history range and per short-term maturity, the
maturity's name and sort order, its yield, the 10-year yield of the same date and the spread (10-year minus short-term,
percentage points), plus `range_start_date` and `range_end_date` for `with_range_dates`. A multi-select filter on the
maturity name (a field filter, default all four) keeps the rows of the chosen maturities; the Vega-Lite chart draws the
10-year as one line (the same value repeats on each maturity's row, so it is drawn from the rows of one maturity: the
first chosen in sort order) and each chosen maturity as a coloured line; the tooltip shows the spread. A field filter is
used, not a parameter, because the dashboards' multi-value parameters are not used anywhere yet and a field filter needs
nothing new. Rates are shown on dates where both the 10-year and the maturity have a value (FRED skips holidays the same
way for all four).

Placement: under the ranking on the Yield Deep Dive, with its own history range selector (the same options as the other
dashboards, 36 months by default), and a line in the page text saying the curve is US Treasury yields only.

### D3. Currency Monitor without the Company Deep Dive

`currency_dashboard.build()` stops adding the page, its datasets, parameters and date binding. The shared test checks
the page in the Market Climate, Inflation-Deflation and Strategy dashboards only.

### D4. Strategy 004 indicators as columns of `price_indicator_daily`

Per listing and price date, over the listing's price rows (trading days):

| Column | Meaning |
|---|---|
| `close_sixty_day_change_amount` | close - close 60 rows earlier (the 60-day rate of change in dollars); empty with fewer than 61 rows |
| `close_sixty_day_change_ratio` | close / close 60 rows earlier - 1 (0.30 = up 30%) |
| `price_range_amount` | high - low |
| `price_range_ratio` | (high - low) / close |
| `true_range_amount` | the largest of high - low, abs(high - previous close) and abs(low - previous close), which equals max(high, previous close) - min(low, previous close); high - low on the listing's first row |
| `true_range_ratio` | true range / close |
| `price_range_sixty_day_average_amount`, `price_range_sixty_day_average_ratio` | simple average of the last 60 rows; empty with fewer than 60 rows |
| `true_range_sixty_day_average_amount`, `true_range_sixty_day_average_ratio` | the same for the true range (the average true range, ATR) |
| `efficiency_r60_ratio` | efficiency ratio *r60*: `close_sixty_day_change_amount` (rate of change 60d amount) / `price_range_sixty_day_average_amount` (*ar* amount SMA60) |
| `efficiency_tr60_ratio` | efficiency ratio *tr60*: `close_sixty_day_change_amount` / `true_range_sixty_day_average_amount` (*atr* amount SMA60) |
| `volume_sixty_day_average_count` | simple average volume of the last 60 rows |

**Units (user, 2026-11-07).** The change and the ranges are kept in amounts and as fractions of the close; the
efficiency ratios use the amounts: the 60-day change in dollars over the 60-day average range (or true range) in
dollars. Dollars over dollars, so the ratio does not depend on the share price. Probe E3 (prd, latest day, a red market):
no member reaches 15 with either ratio (90th percentile of *r60* 5.2, highest *r60* 13.3 and *tr60* 10.3). Probe E1 had
compared the change in percent with the range in dollars (a mixed ratio); it is kept only as a record.

**Prices.** Everything uses the reported high, low and close, which Yahoo already corrects for splits (probe E2: no
day-to-day jump over 45% from a split in prd's history), so the change and the ranges are in the same dollars; a dividend
shows as a small fall in the 60-day change.

## Risks / Trade-offs

- [A field filter on a chart with the 10-year drawn from one maturity's rows] → if the filter leaves no maturity, the
  chart is empty; the filter's default is all four.
- [`price_indicator_daily` grows by 14 columns and its run takes longer] → one more window pass over `price_daily`
  (the run time is compared before and after in dev).
- [`fred` loads four full histories once] → four requests; FRED's limits are far above that.

## Migration Plan

Merge; CI deploys prd and runs `fred` then `investments`; the user opens the Yield Deep Dive. Rollback: revert; the extra
FRED rows stay in bronze and are harmless.

## Open Questions

None.
