## Why

Change 3 of the macro prices story: Australian consumer prices next to the US CPI
(`fred-cpi`), so the silver domain can carry both into `market_rate_daily`
(change 4). The ABS publishes the CPI through its Data API, free and with no key.
Probe P4 (`references/poc/macro-prices/p4_abs_cpi.py`) found two series of the
all-groups index for Australia: quarterly from 1948-Q3 and monthly from 2024-04.
Neither is in RBA's or FRED's tables, so this is a new source, `abs`.

## What Changes

- New source `abs`, run by job `run_abs` with the `verify` parameter. It has the same
  shape as `fred`:
  - A **fetch notebook** (`src/common/fetch_abs.py`) requests each series in
    `src/common/abs_series.py` from the ABS Data API, dataflow `ABS,CPI,2.0.0`, as CSV
    with labels. The two series are the all-groups index for Australia, original
    (not seasonally adjusted): `1.10001.10.50.Q` (quarterly) and `1.10001.10.50.M`
    (monthly). The notebook writes one dated JSON Lines file into `bronze_abs.s3_raw`.
  - **Every run fetches the whole of both series** (about 343 rows), with no
    incremental request and no `reload` parameter. When the ABS rebases the index, it
    restates every earlier value; a full fetch keeps them right.
  - **Bronze raw**: append-only Auto Loader `bronze_abs.observations_raw`.
  - **Bronze Publish**: `bronze_abs_publish.observations_scd1`, SCD1 by `series_key`
    and `time_period`.
  - **Silver Landing**: `silver_landing.abs__observations` via `land_changes`.
    `time_period` stays text (`1948-Q3`, `2024-04`) because it is a quarter or a
    month, not a date. Change 4 turns it into the first day of its period.
- Bundle variable `abs_api_url` (`https://data.api.abs.gov.au/rest`) in both
  edition files and the regenerated `databricks.yml`.
- Checks: `verification/bronze_checks/abs.yml`,
  `verification/silver_landing_checks/abs.yml`; design pattern register entries.
- Docs: CLAUDE.md "Sources", `data-sources.md`, a new `source_systems/abs.md`.
- Not in this change:
  - the seasonally adjusted monthly series (the API returns `NoRecordsFound` for
    `1.10001.20.50.M`);
  - trimmed mean and the other CPI measures;
  - the states and capital cities;
  - any carry-forward to days (change 4);
  - Silver Normalised.

## Capabilities

### New Capabilities
- `abs-cpi-ingestion`: fetch the ABS CPI series into append-only raw files and one
  long table, with Bronze Publish and Silver Landing.

### Modified Capabilities
<!-- none: the Landing checks are one new file per source already -->

## Impact

- New:
  - `src/common/abs_series.py` (rows from the CSV, unit tests) and
    `src/common/fetch_abs.py` (notebook);
  - the code folders `src/layers/bronze/abs/`, `src/layers/bronze/abs_publish/` and
    `src/layers/silver/landing/abs/`;
  - two pipelines and job `run_abs`;
  - two check files.
- **Tables**: 3 streaming tables per target, 12 slots of the 500-table quota. The live
  count is 474 (2026-11-03), so this takes it to about 486, just under the stop line
  of 488. Change 4 should add no materialized table, or a clean-up must come first.
- **Schemas**: two new (`bronze_abs`, `bronze_abs_publish`). Live counts are dev 38
  and prd 36 of the 50 allowed per catalog.
- **Rows**: about 343 per run (313 quarterly, 30 monthly) and the same into raw on
  every run. Publish and Landing grow by about one row a month.
- **Network**: two GETs of `data.api.abs.gov.au` per run.
- **CI**: the new resources select only `run_abs`.

## Cross-repo dependencies

Depends on a new iac change, `abs-schemas-volume`, in `demo-databricks-iac`. It adds:
- the schemas `bronze_abs` and `bronze_abs_publish` in both deployments, with the CI/CD
  writable grants;
- the volume `bronze_abs.s3_raw` and its grants, as `raw-volume-fred` did.

It must be applied before this change deploys to dev.

## Model

Sonnet for the implementation. The shape repeats `fred` (fetch notebook, dated files
in a volume, Auto Loader raw, Auto CDC Publish, change-feed Landing).
