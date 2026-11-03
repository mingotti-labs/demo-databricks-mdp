## Context

See proposal.md. Probe P4 (`references/poc/macro-prices/p4_abs_cpi.py`,
`p4_result.txt`) ran from a laptop, not from serverless:

- The dataflow structure lives at `/dataflow/ABS/CPI/2.0.0` (slash form), and its data
  at `/data/ABS,CPI,2.0.0/<key>` (comma form). The key is
  `MEASURE.INDEX.TSEST.REGION.FREQ`.
- `format=csvfilewithlabels` returns a code column and a label column for every
  dimension, plus `TIME_PERIOD`, `OBS_VALUE`, `UNIT_MEASURE`, `OBS_STATUS`,
  `BASE_PERIOD` and others.
- The rows come back unsorted.
- `1.10001.10.50.Q` has 313 rows, from 1948-Q3 to 2026-Q3 (103.64).
- `1.10001.10.50.M` has 30 rows, from 2024-04 to 2026-09 (104.34). Both are original
  index numbers on the latest reference base.
- `1.10001.20.50.M` (seasonally adjusted, monthly) answers 404 `NoRecordsFound`.
- Requesting everything (`/all`) is 45 MB. Per series it is a few KB.

The `fred` source is the template: `src/common/fetch_fred.py`, `fred_series.py`,
`src/layers/bronze/fred/`, `fred_publish/`, `silver/landing/fred/`, job `run_fred`.

## Goals / Non-Goals

**Goals:**
- Both series in Landing, as the ABS sent them, with room to add a series by naming
  its key.
- Raw files that replay without calling the ABS.

**Non-Goals:**
- Typed values, period dates, carry-forward to days (change 4). Other CPI measures,
  regions or seasonal adjustment.

## Decisions

**D1. The same shape as `fred`.** One long table `observations`, so a further series
costs no table. Columns: `series_key`, `time_period`, `value`, `measure`, `index`,
`adjustment_type`, `region`, `frequency`, `unit`, `base_period`, `obs_status`,
`ingested_timestamp`. The labels are taken from the CSV's label columns (`Measure`,
`Index`, `Adjustment Type`, `Region`, `Frequency`, `Unit of Measure`,
`Reference Base Period`). The codes are already in `series_key`. `STRUCTURE*` and
`ACTION` describe the response, not the data, and are left out.

**D2. A full fetch every run.** The two series are about 343 rows. Since the ABS
restates the whole history when it rebases the index, a full fetch needs no `reload`
parameter and no lookback rule. Raw grows by about 343 rows a run. The bronze check
compares the latest file per key, as `fred.yml` does (`compare_latest_file_per`).
Rejected: an incremental `startPeriod`. It would save a few KB, but then a rebase would
need a hand reload.

**D3. One request per series, CSV with labels.** The fetch uses `requests`, with no new
dependency. Rows are built with the `csv` module from the response text. A non-200
status, or no rows, fails the task, and the error names the series key and status.
Every series is fetched before any file is written, so a failed request leaves nothing
behind.

**D4. `time_period` stays text in Landing.** It is a quarter or a month (`1948-Q3`,
`2024-04`), not a date. FRED's Landing types `observation_date` because it is a date.
Change 4 turns a period into its first day, where carry-forward needs it.
Rejected: a derived `period_start` column in Landing. Landing only types columns; it
does not derive new ones.

**D5. The series list is in code**, as `SERIES = ["1.10001.10.50.Q", "1.10001.10.50.M"]`
in `abs_series.py`. The dataflow `ABS,CPI,2.0.0` is a constant there. The base address
is the bundle variable `abs_api_url`.

**D6. CI runs `run_abs` after a deploy.** The API is free, and a run is two calls.

**D7. Bronze Publish is an SCD1 snapshot of the latest file, not `fred`'s streaming
SCD1 (changed during implementation).** The first version copied `fred`'s streaming SCD1,
sequenced by the fetch time. That suits a source whose files hold only part of the data.
The ABS sends the whole history every run, so the fetch time changes on every row and
SCD1 rewrote all 343 rows, and Landing restamped `transformed_timestamp` on all of them,
with no value changed (seen in the second dev run). The repo's rule is that a step stamps
only rows it changes. For a full load the fix is a snapshot flow
(`create_auto_cdc_from_snapshot_flow`) from a view over the latest file without the
fetch time; Auto CDC then writes only changed rows and Landing reads the change feed.
SCD2 (the bronze full pattern, as acnc and SEC) was tried first and rejected by the user:
the series is a full-load latest-value table, raw already keeps every earlier fetch, so
closed versions add little. Consequence: Publish and Landing carry no `ingested_timestamp`
(it would change every row every run); raw keeps it. The pattern is
`bronze_publish_scd1_autocdc_snapshot_python`. A removed period is deleted from Publish.

## Risks / Trade-offs

- [Serverless cannot reach `data.api.abs.gov.au`, or it is slow to answer] -> Task 1.1
  re-runs P4's two series requests from serverless before any code is written.
- [The ABS changes the dataflow version, for example to 2.1.0] -> The request fails
  with 404, and the version is bumped in code.
- [A label changes, for example after a rebase] -> SCD1 takes the latest; raw keeps the
  history.
- [The quota after this change is about 486 of 500] -> Change 4 should use a temporary
  view or join inside `market_rate_daily` (no new materialized table), or a clean-up
  comes first.

## Migration Plan

1. iac `abs-schemas-volume` is applied: schemas `bronze_abs`, `bronze_abs_publish` and
   volume `bronze_abs.s3_raw` exist in `mdp_dev` and `mdp_prd`.
2. A draft PR deploys to dev. `run_abs` runs as the service principal with
   `verify=true`, then once more, so that Publish and Landing counts stay the same.
3. Merge. CI runs `run_abs` in prd.

Rollback: remove the code; drop the three tables per target, with approval.

## Dev results (2026-11-03)

Filled in after the SCD2 correction (D7) is verified.
