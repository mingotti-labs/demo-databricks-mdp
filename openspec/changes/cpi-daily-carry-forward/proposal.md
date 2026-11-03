## Why

Change 4 and last step of the macro-prices story. CPI is in Silver Landing for the US
(`fred__observations`: CPIAUCNS, CPIAUCSL, CPILFESL, monthly) and Australia
(`abs__observations`: monthly and quarterly all-groups, original). It is one value per
period, so it cannot be joined by date to the daily rates, and a 200-day average (a later
step) needs one value per day. This change puts CPI into `market_rate_daily` on
business days.

## What Changes

- `market_rate_daily` gains five CPI `rate_code`s and one column, `is_carried_forward`
  (false on every existing rate row, true on a CPI row that repeats an earlier value):
  - `au_cpi_all_groups_monthly` (ABS `1.10001.10.50.M`)
  - `au_cpi_all_groups_quarterly` (ABS `1.10001.10.50.Q`)
  - `us_cpi_all_items_not_seasonally_adjusted` (FRED `CPIAUCNS`)
  - `us_cpi_all_items_seasonally_adjusted` (FRED `CPIAUCSL`)
  - `us_cpi_excluding_food_and_energy_seasonally_adjusted` (FRED `CPILFESL`)
  - unit `index_points`.
- **Carry-forward**: a value starts on the first business day (Monday to Friday) on or
  after the first day of its period (`2026-09` is 2026-09-01; `2026-Q3` is 2026-07-01) and
  repeats on each business day until the next period starts. The first row of a period
  has `is_carried_forward` false; the rows after it are true. The last value repeats up
  to the latest date of the daily rates already in the table.
- Existing rates are unchanged: no weekend or holiday rows are added.
- No new table: still the one materialized view. The quota stays where it is.
- Not in this change: the 200-day average (later), country trading-day calendars (a
  later swap of the date spine), CPI sub-indexes, Brazil and NZ.

## Capabilities

### Modified Capabilities
- `silver-domain-investments`: `market_rate_daily` carries CPI and the flag.

## Impact

- `src/layers/silver/domain/investments/market_rate_daily.py`, `src/common/investments.py`
  (the CPI list), `verification/verify_silver_domain_investments.py`, docs
  (`data-sources.md`, `silver.md` column naming).
- Rows: about 85,000 added (five series back to 1913, 1947, 1957 and 1948 at about 260
  rows a year). Existing rows are untouched.
- Runs: `run_investments` only (it reads Landing; `run_fred` and `run_abs` are not
  affected).
- Look-ahead, accepted: a value sits on the dates of the period it measures, not its
  publication date, which the raw data does not hold. The table describes; it is not
  point-in-time and must not be used for prediction. Recorded in the design.

## Model

Sonnet: one SQL view change on a defined shape, with a verification.
