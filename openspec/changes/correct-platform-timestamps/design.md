## Context

Evidence and measurements are in proposal.md. Draft PR #86 is the silver
experiment (not for merge).

## Decisions

- **D1 Stamp where changes are detected.** `current_timestamp()` only on rows a
  step inserts, modifies or closes; never on a full snapshot.
- **D2 Bronze SCD2 via a `MERGE` job task** (pattern
  `bronze_publish_scd2_merge_python`). Change detection on the business columns
  (every column except the platform and validity columns), keyed by ABN.
  Rejected: deriving the timestamps from snapshot Auto CDC's `__START_AT` and
  `__END_AT`; that gives the SCD2 step's time, not raw's fetch time, so
  `ingested_timestamp` would not be exact.
- **D3 Silver Landing: incremental from the change feed** (pattern
  `silver_landing_change_feed_python`). A streaming table in the silver pipeline
  reads `charity_register_scd2` with `readChangeFeed`, keeps the post-change
  rows, and applies them by key (`ABN`, `scd_valid_from_timestamp`) with
  `create_auto_cdc_flow`. `current_timestamp()` is stamped in the stream, which
  carries only changed rows. Change data feed is enabled on the SCD2 table.
- **D4 Silver Normalised: full rebuild that keeps timestamps** (pattern
  `silver_rebuild_keep_timestamps_python`). For each table: build the new rows,
  left-join the previous table on all business columns; matched rows keep the
  old `transformed_timestamp`, the others get `current_timestamp()`; overwrite.
  Chosen over incremental refresh because these tables are mostly distinct
  values and counts, full rebuilds are cheap at this size (measured), and the
  result is simpler to reason about.
- **D5 Silver's `ingested_timestamp`** is carried from its input. Aggregating
  Normalised tables (extracted entities, `value_lineage`) take `min()`: the
  first ingest that contributed to the row. `max()` was only chosen because
  `_raw` restamped every run; with each SCD2 version keeping its own fetch time,
  `min()` is meaningful. In the D4 comparison, every column except
  `transformed_timestamp` counts, so a change in `ingested_timestamp` also
  gives the row a new `transformed_timestamp = current_timestamp()`.
- **D6 Backfill** of existing SCD2 versions, as stated in proposal.md.

## Probes (dev, before any migration)

- **P1** Removing a dataset from a pipeline's code: is the table dropped or left
  in place? Decides the migration steps.
- **P2** The SCD2 `MERGE` on a copy of `charity_register_scd2` in the dev-only
  `pattern_bronze_publish` schema: two runs with no change write 0 rows; a
  simulated change closes one version and inserts one.
- **P3** The Normalised rebuild on a copy: a second run with no change keeps
  every `transformed_timestamp`; a changed row gets a new one.
- **P4** Landing from the change feed, on the P2 copy: after a simulated change,
  Landing equals a full read of the SCD2 copy row for row (zero difference in
  both directions), and only the changed rows got a new `transformed_timestamp`.

## Probe results

- **P1 (2026-10-22, dev, throwaway pipeline `probe--dataset-removal--dev` in the
  patterns bundle):** removing a dataset from the pipeline code and running
  again leaves the table in place, with its rows, still a materialized view
  still tied to the pipeline (`pipeline_id` unchanged). So removal loses no
  data, but the table stays pipeline-owned: the migration copies it out, drops
  it and recreates it as a plain Delta table.
- **P2 (2026-10-22, dev, copy `pattern_bronze_publish.probe_scd2` of
  `charity_register_scd2` with the D6 backfill, source `charity_register_raw`
  with non-null ABN, `src/common/scd2_merge.py`):** two runs with unchanged raw
  wrote 0 rows each (Auto CDC rewrote 65,907 in the same situation). After
  editing one current row, adding a fake key and deleting one key on the copy,
  one run inserted 2 and updated 2: the edited key closed and got a new version,
  the deleted key was inserted, the fake key was closed. Inserted versions carry
  raw's `ingested_timestamp`; only those 4 rows got the run's
  `transformed_timestamp`; current rows stayed 65,907.

## Migration (per environment, dev first)

1. Back up the SCD2 table and the Normalised tables (`DEEP CLONE`).
2. Remove the datasets from the pipelines (P1 decides whether each table
   survives).
3. Recreate them as plain Delta tables under the same names from the backups,
   with the D6 backfill, owned by the CI/CD service principal.
4. Drop the Landing materialized view; the silver pipeline recreates it as a
   streaming table from the SCD2 table's change feed.
5. Run `run_acnc`, verify, then drop the backups (approval).

## Risks

- Losing SCD2 history: mitigated by the backup and by checking row counts and
  closed versions before the backup is dropped.
- Ownership and permission errors: the job runs as the CI/CD service principal,
  as today.
