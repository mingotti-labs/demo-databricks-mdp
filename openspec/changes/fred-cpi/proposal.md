## Why

Before gold, the dividend portfolio story needs inflation next to the rates it
already has, so prices and yields can be compared in real terms. The US measure is
the consumer price index for all urban consumers (CPI-U), published monthly by the
Bureau of Labor Statistics and republished by FRED. The `fred` source already
fetches daily rates from FRED into one long table; a new series is one more name in
its list, and the fetch loads a series' full history the first time it sees it.

This is the first of four changes agreed on 2026-11-02 (macro prices): (1) US CPI
from FRED, (2) gold, commodity and CRB prices from Yahoo, (3) Australian CPI from
the ABS, (4) a silver domain step that turns monthly and quarterly values into daily
rows in `market_rate_daily`, carried forward from the start of their period. The
probes for all four ran before this proposal (`references/poc/macro-prices/`,
P1 to P4 in the probes register) and are committed with it.

## What Changes

- `SERIES` in `src/common/fred_series.py` gains three monthly series:
  - `CPIAUCSL`: CPI-U, all items, seasonally adjusted (from 1947-01).
  - `CPIAUCNS`: CPI-U, all items, not seasonally adjusted (from 1913-01); the series
    year-on-year inflation is usually read from, never revised.
  - `CPILFESL`: CPI-U, all items less food and energy ("core"), seasonally adjusted
    (from 1957-01).
- No code, table, pipeline or job changes: rows land in the existing
  `bronze_fred.observations_raw`, `bronze_fred_publish.observations_scd1` and
  `silver_landing.fred__observations`, told apart by `series_id`, with `frequency`
  `Monthly` and `observation_date` the first day of the month.
- Documentation: the FRED source system file, the data sources register,
  CLAUDE.md "Sources", the spec's list of series.
- The macro-prices probe scripts and results (`references/poc/macro-prices/`) and
  their probes register rows.
- Not in this change: CPI in `market_rate_daily` and the daily carry-forward step
  (change 4), year-on-year inflation or any other calculation (silver domain).

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `fred-rates-ingestion`: the series fetched add the three CPI series.

## Impact

- Tables: none new; 0 slots of the 500-table quota (474 on 2026-11-02).
- First run after the merge: about 3,160 new rows (`CPIAUCSL` 957, `CPIAUCNS`
  1,365, `CPILFESL` 837, per probe P2); later runs add about 3 rows a month.
- Network: two more GETs per series per run (six), well under FRED's 120 a minute.
- CI: only `fred_series.py` changes in `src/`, which only `run_fred` uses, so the
  merge runs `run_fred` alone in prd (to be confirmed with `cicd/affected_units.py`
  during implementation).

## Cross-repo dependencies

None: the `fred` secret scope, the `bronze_fred.s3_raw` volume and every schema
exist already.

## Model

Sonnet: one list entry, tests and documentation, then the usual dev run.
