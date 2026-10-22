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

## What the timestamps mean (corrected definition)

- `ingested_timestamp`: the fetch time of the data. On `_raw`, every row (a full
  reload re-fetches every row). On an SCD2 version, the fetch that created that
  version, fixed forever, so a row's story is readable in one table.
- `transformed_timestamp`: when this table's step inserted, modified or closed
  the row. A row the step did not touch keeps its previous value.

## What Changes (acnc first, as the reference implementation)

- **Bronze SCD2 by `MERGE`, not snapshot Auto CDC.** A job task after the bronze
  pipeline compares `charity_register_raw` (non-null ABN) with the current SCD2
  rows on the business columns: a changed row closes the old version and inserts
  a new one, a new key inserts, a vanished key closes. Inserted versions carry
  raw's exact `ingested_timestamp`; `transformed_timestamp = current_timestamp()`
  only on inserted and closed rows. Unchanged rows are not written. Snapshot
  Auto CDC has no way to add a value only on the rows it changes, which is why
  it is replaced. Same shape as neon's existing `scd2_merge` job.
- **Silver Landing incremental, from bronze's changes.** Landing is one row per
  bronze SCD2 row, so it reads only the rows the bronze `MERGE` changed (the SCD2
  table's change data feed) and applies them by key, as a streaming table in the
  silver pipeline. `transformed_timestamp = current_timestamp()` is stamped in
  that stream, where only changed rows pass, so only they get it.
- **Silver Normalised as a full rebuild that keeps timestamps.** Its tables are
  mostly distinct values and counts across many rows. Measured on acnc: a full
  rebuild of all silver tables costs 77 s of table work against 42 s for a run
  with nothing to do; start-up (86 to 148 s) dominates. So each Normalised table
  is rebuilt from its current definition and compared with the previous table
  on the business columns: unchanged rows keep their `transformed_timestamp`,
  new or changed rows get `current_timestamp()`, rows that are gone are
  removed. A materialized view cannot read its own previous result, so
  Normalised becomes a job task after the silver pipeline (one shared notebook
  reusing today's `transforms.py` functions).
- **Existing history backfilled once.** The original fetch times of existing
  versions were overwritten and cannot be recovered. Existing versions get
  `ingested_timestamp = __START_AT` and
  `transformed_timestamp = coalesce(__END_AT, __START_AT)`, the best available
  values, recorded in the decision register.
- **Docs**: NAMING.md "Platform-added timestamp columns", silver.md and a
  decision-register entry state the corrected definition; the patterns register
  and `design_patterns.yml` get the new pattern IDs.
- **Out of scope**: SCD1 tables (unchanged for now); the other sources (one
  change each, once acnc is proven); performance work beyond removing the
  per-run rewrites.

## Capabilities

### New Capabilities
- `platform-timestamps`: what `ingested_timestamp` and `transformed_timestamp`
  mean and when they may be written.

### Modified Capabilities
- `pipeline-per-layer`: acnc's silver pipeline holds Landing only; Normalised
  is a job task (updated at archive time).

## Model

Opus to implement acnc: it sets the convention and includes a table migration.
Sonnet for the later per-source rollouts.

## Impact

- **Table migration, with approval.** The acnc SCD2 table and the 17
  Normalised tables are owned by pipelines today, and a job cannot write to
  them. They are backed up, removed from the pipelines and recreated as plain
  Delta tables under the same names. SCD2 history is kept through the backup.
  The Landing table changes from a materialized view to a streaming table, so
  it is dropped and rebuilt from bronze; it holds no history of its own, and its
  first run stamps every row (they are all inserted then). Every drop needs
  explicit approval. Probes come first (design.md).
- prd: the same migration after dev is verified, through the prd approval gate.
- Verification jobs keep their checks; the null `transformed_timestamp` on the
  10 pre-retrofit closed versions goes away with the backfill.
- Table count: temporary backups (+19 in one environment at a time).
