## Why

Step 8 of the dividend portfolio story (`demo-databricks-planning`): the rate
comparison sets the shortlist's yield against the US 10-year Treasury yield as
well as the RBA cash rate, over time. FRED (the St. Louis Fed's database)
publishes it as series `DGS10`, daily since 1962, through a free REST API that
needs a key. The `fred` secret scope with `api_key` and the CI/CD principal's
READ on it already exist (iac `dividend-portfolio-schemas`). Probe P1 (run
2026-10-31, before this proposal) called the API from serverless with that key.

## What Changes

- New source `fred`, run by job `run_fred` with the `verify` and `reload`
  parameters, the same shape as `rba`:
  - A **fetch notebook** (`src/common/fetch_fred.py`) reads the key from
    `dbutils.secrets.get("fred", "api_key")`, calls `series` (title, units,
    frequency) and `series/observations` for each series in
    `src/common/fred_series.py` (`DGS10` today), drops the `.` values FRED
    returns for days with no data, and writes one dated JSON Lines file into
    `bronze_fred.s3_raw`.
  - **Incremental**: after the first run only observations from 31 days before
    the series' last stored date are requested (`observation_start`); the job
    parameter `reload=true` requests everything.
  - **Bronze raw**: append-only Auto Loader `bronze_fred.observations_raw`
    (pattern `bronze_volume_append_autoloader_python`).
  - **Bronze Publish**: `bronze_fred_publish.observations_scd1`, SCD1 by
    `series_id` and `observation_date` (pattern
    `bronze_publish_scd1_autocdc_stream_python`).
  - **Silver Landing**: `silver_landing.fred__observations` via `land_changes`,
    with `observation_date` as a DATE (the user's rule for RBA, applied here);
    `value` and the rest stay text.
- Bundle variable `fred_api_url` (`https://api.stlouisfed.org/fred`) in both
  edition files and the regenerated `databricks.yml`.
- Verification spec, Landing verification entry, design pattern register,
  CLAUDE.md "Sources", source system file.
- Not in this change: other FRED series (add a name to the list), any
  conversion or calculation (silver domain), Silver Normalised.

## Capabilities

### New Capabilities
- `fred-rates-ingestion`: fetch FRED series incrementally into append-only raw
  files and one long table, with Bronze Publish and Silver Landing.

### Modified Capabilities

## Impact

- New: `src/common/fred_series.py` (rows from the API payloads, unit tests),
  `src/common/fetch_fred.py` (notebook), `src/layers/bronze/fred/`,
  `src/layers/bronze/fred_publish/`, `src/layers/silver/landing/fred/`, two
  pipelines, job `run_fred`, `verification/bronze_checks/fred.yml`.
- Tables: 3 per target, all streaming tables, 12 slots of the 500-table
  quota (422 on 2026-10-31).
- First load 16,192 rows (16,913 less 721 days FRED has no value); about 20
  rows a run after.
- Network: two GETs of `api.stlouisfed.org` per series per run. FRED allows
  120 requests a minute.
- Adding the Landing entry to `verification/verify_silver_landing.py`, a notebook
  every unit's `verify_silver` step runs, makes CI run every such unit in prd
  after the merge (about 45 minutes, as the RBA merge did).

## Cross-repo dependencies

Depends on `raw-volume-fred` in `demo-databricks-iac`: it adds the volume
`bronze_fred.s3_raw` and its grants, and must be applied before this change
deploys to dev. The `fred` secret scope and the schemas `bronze_fred`,
`bronze_fred_publish` and `silver_landing` exist already.

## Model

Sonnet: the shape repeats RBA and Yahoo (fetch notebook, dated files in a
volume, Auto Loader raw, Auto CDC Publish, change-feed Landing).
