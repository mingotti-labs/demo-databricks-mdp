## Why

The platform timestamps are implemented incorrectly. `current_timestamp()` is
applied to the full snapshot before any change check, so every run stamps every
row, whether it changed or not. Evidence from `dev` (acnc, 2026-10-22):

- `bronze_acnc_publish.charity_register_scd2`: runs that created no new version
  (0 inserted) still updated all 65,907 current rows (Delta history versions 10
  and 14). `track_history_except_column_list` prevents spurious versions, but
  the excluded columns are still rewritten in place.
- So current rows show the latest fetch as `ingested_timestamp`, not the fetch
  that created the version: a row's story cannot be read from the table.
- Silver: all 17 acnc tables are fully rebuilt on every run, even with unchanged
  input, because `current_timestamp()` makes them non-deterministic. With the
  timestamps removed (draft PR #86) the same run does nothing (`NO_OP`).
- NAMING.md encodes the mistake ("last transformed at", restamped at every
  layer).

Root cause at bronze, from the Databricks CDC docs: changes in columns not
tracked for history "overwrite the current row instead of creating a new
version". acnc passed `ingested_timestamp`, new on every full load, into the
snapshot as such a column. The cause was that column, not snapshot Auto CDC
(probe P5, design.md).

## What the timestamps mean (corrected definition)

- `ingested_timestamp`: the fetch time of the data. On `_raw`, every row (a full
  load re-fetches every row). Downstream, the fetch that created the row's
  version, fixed forever.
- `transformed_timestamp`: when this table's step inserted, modified or closed
  the row. A row the step did not touch keeps its previous value.

## What Changes (acnc first, as the reference implementation)

The first implementation (#88) replaced snapshot Auto CDC with a `MERGE` job
task. Probes P5 to P8 (design.md) showed standard Auto CDC works once the
per-load column is kept out of the snapshot, so bronze goes back into the
pipeline:

- **Bronze full pattern.** `_raw` is a full load (a materialized view), so every
  row's `ingested_timestamp` changes on every load. That column is never part
  of the snapshot. Bronze Publish SCD2 is standard
  `create_auto_cdc_from_snapshot_flow` from a temporary view over
  `charity_register_valid` without `ingested_timestamp` (nor the SCD1 stamp
  `transformed_timestamp`). Auto CDC versions each snapshot with the pipeline
  update's time: `__START_AT` on the versions it inserts, `__END_AT` on the
  ones it closes; unchanged rows are not written. The SCD2 table has no
  platform timestamp columns. Streaming Auto CDC is not an option (a
  materialized view cannot be streamed, P8), and neither is a function source
  carrying raw's exact fetch time (it cannot read a dataset of its own
  pipeline, design.md D7).
- **Silver Landing settles both timestamps.** A streaming table reading the SCD2
  table's change feed, so it receives only the versions Auto CDC inserted or
  closed (as today, #88). It stamps `transformed_timestamp = current_timestamp()`
  in that stream and sets `ingested_timestamp = __START_AT`, kept alongside
  `scd_valid_from_timestamp` (same value, the standard column name).
- **Silver Normalised: unchanged for now** (the #88 rebuild task that keeps
  timestamps). It reads `ingested_timestamp` from Landing, which keeps it.
  Revisited separately (task 5.6).
- **New load, no migration.** This is a test platform: acnc's current SCD2
  table, its backup and Landing are dropped in dev and prd (approved
  2026-10-23) and rebuilt from one load. Existing SCD2 history is lost.
- **Retired**: the `scd2_merge` task, `src/common/scd2_merge.py`,
  `src/layers/bronze/scd2_merge.py`, the #88 migration task and its notebook.
- **No pipeline retries, acnc first**: acnc's two pipelines set both retry
  settings to `"0"`; a failed update fails once instead of repeating the same
  error. The other pipelines follow in the rollout change (changing them here
  would make CI run every unit in prd).
- **Docs**: NAMING.md "Platform-added timestamp columns", the patterns register
  (the bronze full pattern stated as such) and `design_patterns.yml`.
- **Out of scope**: SCD1 tables; the other sources (one change each, once acnc
  is proven); performance work.

## Capabilities

### New Capabilities
- `platform-timestamps`: what `ingested_timestamp` and `transformed_timestamp`
  mean and when they may be written.

### Modified Capabilities
- `pipeline-per-layer`: acnc's silver pipeline holds Landing only; Normalised
  is a job task (updated at archive time).

## Model

Sonnet to implement: it applies the agreed design and the probed code (P6, P7).

## Impact

- **Drops, approved 2026-10-23 for dev and prd**:
  `bronze_acnc_publish.charity_register_scd2` (plain Delta today; recreated as
  a streaming table by the bronze pipeline), `charity_register_scd2_backup`
  and `silver_landing_acnc.charity_register` (its stream reads the old table's
  change feed). Normalised tables are kept; their first run after the new load
  restamps every row once, since `ingested_timestamp` changes.
- prd: same, through the prd approval gate after dev is verified.
- Verification jobs: checks on the SCD2 table's platform columns move to
  Landing.
