## Why

Step 7 of the dividend portfolio story (`demo-databricks-planning`). The
portfolio view converts USD amounts to AUD (cost, value, dividend income), and
the rate comparison sets the shortlist's yield against the RBA cash rate over
time. The RBA publishes them, and the rates that follow the cash rate, as free
CSV files at fixed addresses, with no key:
- F11.1: daily exchange rates, 23 currencies, from 2023-01-03;
- F1: daily money market rates, including the cash rate target, from 2011-01-04;
- F2: daily Australian government bond yields (2, 3, 5 and 10 years and
  indexed), from 2013-05-20;
- F5: monthly indicator lending rates, from 1959-01-31: bank housing loans
  (variable standard, discounted and interest-only, 3-year fixed;
  owner-occupier and investor), mortgage managers, securitised loans, and
  personal, credit card and business lending.

Checked from a local machine on 2026-10-31; probe P1 checks the same from
serverless.

## What Changes

- New source `rba`, run by job `run_rba` with the `verify` parameter:
  - A **fetch notebook** (`src/common/fetch_rba.py`) downloads the four files
    (`f11.1-data.csv`, `f1-data.csv`, `f2-data.csv`, `f5-data.csv`), turns each
    into long rows (one per series and date, empty cells skipped, values kept
    as text) and writes one dated JSON Lines file per table into `bronze_rba.s3_raw`. Each row carries the series' metadata from
    the file's header (title, description, frequency, type, units, source,
    publication date).
  - **Incremental**: per table, only rows dated from 31 days before the last
    stored date are written (late values and revisions land again). A first run,
    or the job parameter `reload=true`, writes every row.
  - **Bronze raw**: one append-only Auto Loader streaming table
    `bronze_rba.observations_raw` (pattern `bronze_volume_append_autoloader_python`).
  - **Bronze Publish**: `bronze_rba_publish.observations` as SCD1 keyed by
    `series_id` and `observation_date`, streaming Auto CDC from raw (pattern
    `bronze_publish_scd1_autocdc_stream_python`, as Yahoo).
  - **Silver Landing**: `silver_landing.rba__observations` via `land_changes`.
- Bundle variable `rba_tables_url` (`https://www.rba.gov.au/statistics/tables/csv`)
  in both edition files and the regenerated `databricks.yml`; the fetch reuses
  `http_user_agent`.
- Verification spec, design pattern register entries, CLAUDE.md "Sources".
- Not in this change: exchange rates before 2023 (only in Excel files), the
  monthly housing rates on outstanding loans (table F6, which writes its dates
  differently), the monthly copies of F2 and F1 (F2.1, F1.1), FRED (step 8), any
  conversion or calculation (the silver domain does it), Silver Normalised
  (one entity, nothing to restructure).

## Capabilities

### New Capabilities
- `rba-rates-ingestion`: fetch RBA tables F11.1, F1, F2 and F5 incrementally into
  append-only raw files and one long table, with Bronze Publish and Silver
  Landing.

### Modified Capabilities

## Impact

- New: `src/common/rba_tables.py` (parser, unit tests), `src/common/fetch_rba.py`
  (notebook), `src/layers/bronze/rba/`, `src/layers/bronze/rba_publish/`,
  `src/layers/silver/landing/rba/`, two pipelines, job `run_rba`,
  `verification/bronze_checks/rba.yml`, Silver Landing verification entry.
- Tables: 3 per target (raw, Publish, Landing), all streaming tables, so 12
  slots of the 500-table metastore quota for dev and prd. The quota read
  458/500 on 2026-10-31, which is why the RBA tables share one long table
  instead of one table per RBA table (that would be 48 slots for four).
- Raw growth: about 1,200 rows a run after the first (the daily series' new
  days, a few hundred rows each table); the first run writes about 90,000 rows.
- Network: four GETs of `www.rba.gov.au` per run.

## Cross-repo dependencies

Depends on `raw-volume-rba` in `demo-databricks-iac`: it adds the volume
`bronze_rba.s3_raw` and its grants. That change must be applied before this
one deploys to dev. The schemas `bronze_rba`, `bronze_rba_publish` and
`silver_landing` exist already.

## Model

Sonnet: the shape repeats SEC and Yahoo (fetch notebook, dated files in a
volume, Auto Loader raw, Auto CDC Publish, change-feed Landing).
