## Why

Change 2 of 4 of the market climate story (planning `docs/superpowers/specs/2026-11-04-market-climate-story-design.md`;
definitions and the worked P/E example in `references/user-stories/monitor-understand-market-climate.md`).
The gold climate (change 3) needs three silver inputs that do not exist yet: each filing's 10-year
average earnings, plain and inflation-adjusted; a 200-day simple moving average of prices; and the
S&P 500 index level (`^GSPC`) for the trend vote. The story also asks for every new column to carry a
Unity Catalog description, so the figures can be audited and Genie can explain them.

## What Changes

- **`^GSPC` benchmark** in `data/portfolio/benchmarks.csv` (kind `market_index`). As a new benchmark it
  loads from 1970 (existing Yahoo rule). Its exchange `SNP` already maps to `XXXX`.
- **`company_fundamentals`, four new columns** per filing row, from the last 10 annual earnings known
  at the filing (`net_income` of the latest 10-K or 10-K/A per fiscal year end filed on or before the
  row's `valid_from_date`):
  - `consumer_price_index_value`: US CPI, all items, not seasonally adjusted, of the latest month on or
    before the row's period end
  - `earnings_ten_year_average_amount`: plain average of those annual earnings
  - `earnings_ten_year_average_inflation_adjusted_amount`: average of each year's earnings x (this
    row's CPI / that year's CPI), in the money of this row's period end
  - `earnings_year_count`: how many years went in (at most 10)
- **`price_indicator_daily`** (new materialized view in the same pipeline): one row per listing and
  price date with the adjusted close, its 200-day simple moving average and that average's 20-day
  slope; empty until 200 (and 220) prices exist.
- **Column descriptions** in Unity Catalog for every new column and every column of the new table
  (what it is, the formula, the units), set in the view definitions.
- **Naming rule**: two new endings, `_ratio` (a quotient: P/E, slope) and `_value` (a measured level
  that is not money: CPI index points, already used by `rate_value`). Spec, `silver.md`.
- Not in this change: market value, index totals, P/E and the yes/no answers (gold, change 3).

## Capabilities

### Modified Capabilities
- `silver-domain-investments`: naming endings; 10-year earnings columns; new `price_indicator_daily`.

## Impact

- Table slots: one materialized view in the existing pipeline, 2 per environment, 4 in all (466 to about 470).
- Run order after merge: CI runs `investments` and `portfolio` (alphabetical); the new benchmark needs
  `portfolio`, then `yahoo`, then `investments`. Run `run_yahoo` and then `run_investments` by hand,
  each started with `--no-wait` and polled to the end (lesson from change 1).
- `price_daily` grows by about 14,000 `^GSPC` rows.

## Model

Sonnet: the definitions are settled in the story and here; the work is SQL in existing views plus one
new view.
