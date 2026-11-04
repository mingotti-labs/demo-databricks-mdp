## Context

Probe P1 of the story (`references/poc/market-climate/p1_pe10_examples.py`, results in
`p1_pe10_examples_result.txt`) computed the 10-year averages ad hoc for Apple and the index; this change
puts the per-filing part into `company_fundamentals` so gold only sums and converts. Member prices
start 2025-10-28 (P2); benchmarks added later load from 1970. CPI rows in `market_rate_daily` sit on
the business days of the month they measure (`cpi-daily-carry-forward`); October 2025 has no US CPI.

## Goals / Non-Goals

**Goals:** per-filing 10-year averages a person can recompute from the filing rows and CPI; a reusable
moving average; descriptions on every new column; no new pipeline.

**Non-Goals:** market value, P/E, index sums (gold); full price history for members; column
descriptions on the existing columns (a later change can add them the same way).

## Decisions

### D1. The 10 years at each filing
For a row with filing date F: take every 10-K and 10-K/A of the company filed on or before F, keep the
latest filed per `period_end_date` (a restatement replaces the original), order by period end and keep
the last 10 with a `net_income`. The average is over those years only; `earnings_year_count` says how
many. A 10-Q row carries the same 10 years as the latest 10-K known at its filing date. Rejected:
trailing 12-month values from 10-Qs (they overlap, and the story defines annual earnings).

### D2. CPI of a period end, and today's money later
`consumer_price_index_value` = the US CPI (`us_cpi_all_items_not_seasonally_adjusted`) of the latest
month on or before the period end that has a value (so a period ending in October 2025 uses September
2025). Each year's factor is this row's CPI / that year's CPI, so the adjusted average is in this row's
period-end money. Gold multiplies by CPI today / `consumer_price_index_value` (today's money changes
monthly and cannot be stored on a filing). Same rule for every year's CPI.

### D3. Moving average on the adjusted close
`price_indicator_daily` uses `price_close_adjusted`, so a split does not break the average; for an
index (`^GSPC`) the adjusted close equals the close. The average is over the listing's last 200 price
rows (trading days, not calendar days) and is empty when fewer exist. Slope = average today / average
20 trading days earlier - 1 (a ratio: 0.012 is +1.2% in about a month); "flat" is a gold threshold, not
fixed here. Columns: `listing_id`, `trading_symbol_code`, `price_date`, `price_close_adjusted`,
`close_adjusted_two_hundred_day_average_amount`, `close_adjusted_two_hundred_day_average_slope_ratio`,
`close_adjusted_day_count` (rows in the window, up to 200), `currency_code`, `ingested_timestamp`.

### D4. Column descriptions in the view definition
`@dp.materialized_view(schema=...)` takes Spark DDL with `COMMENT` per column, so descriptions are written
with the table, not by a separate ALTER (which a refresh could overwrite). Probe P1 (2026-11-04, dev,
`references/poc/market-climate-silver/`): a `schema=` listing only some columns is rejected ("incompatible
with the schema inferred from its query"); listing every column works and the comments reach Unity Catalog.
So `company_fundamentals` takes its DDL from the query's inferred schema (`spark.sql(FILINGS).schema`, an
analysis of Landing tables only, no data read) with descriptions merged in from one dictionary in
`src/common/investments.py`; columns without an entry keep no description. `price_indicator_daily` reads
`price_daily`, a dataset of the same pipeline that does not exist yet while the graph is built, so its
(short) schema is written out.

### D5. Naming endings
`_ratio` for a quotient, `_value` for a measured level that is not money (CPI points; `rate_value`
already uses it). Numbers in names are words (`ten_year`, `two_hundred_day`).

## Risks / Trade-offs

- [The 10-year window per filing is a self-join of filings to earlier 10-Ks] -> about 500 companies x
  70 filings x 10 years; small.
- [A company's first years have fewer than 10 annual earnings] -> `earnings_year_count` shows it; gold
  counts such members.
- [A declared schema must match the query] -> the DDL is generated from the inferred schema, so a new
  column cannot be forgotten; a column renamed in the query without its description entry keeps no comment
  (a test lists the described columns that no longer exist).

## Migration Plan

Merge -> CI runs `investments`, `portfolio` -> by hand `run_yahoo`, then `run_investments` (each
`--no-wait`, polled) in prd; same order in dev before merge. Rollback: revert; the `^GSPC` raw rows are
harmless.

## Open Questions

None.
