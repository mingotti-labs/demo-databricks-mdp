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
- **D3 Silver: full rebuild that keeps timestamps** (pattern
  `silver_rebuild_keep_timestamps_python`). For each table: build the new rows,
  left-join the previous table on all business columns; matched rows keep the
  old `transformed_timestamp`, the others get `current_timestamp()`; overwrite.
  Chosen over incremental refresh because full rebuilds are cheap at this size
  (measured) and simpler to reason about.
- **D4 Silver's `ingested_timestamp`** is carried from its input, as today
  (`max()` for aggregating tables).
- **D5 Backfill** of existing SCD2 versions, as stated in proposal.md.

## Probes (dev, before any migration)

- **P1** Removing a dataset from a pipeline's code: is the table dropped or left
  in place? Decides the migration steps.
- **P2** The SCD2 `MERGE` on a copy of `charity_register_scd2` in the dev-only
  `pattern_bronze_publish` schema: two runs with no change write 0 rows; a
  simulated change closes one version and inserts one.
- **P3** The silver rebuild on a copy: a second run with no change keeps every
  `transformed_timestamp`; a changed row gets a new one.

## Migration (per environment, dev first)

1. Back up the SCD2 table and the silver tables (`DEEP CLONE`).
2. Remove the datasets from the pipelines (P1 decides whether each table
   survives).
3. Recreate them as plain Delta tables under the same names from the backups,
   with the D5 backfill, owned by the CI/CD service principal.
4. Run `run_acnc`, verify, then drop the backups (approval).

## Risks

- Losing SCD2 history: mitigated by the backup and by checking row counts and
  closed versions before the backup is dropped.
- Ownership and permission errors: the job runs as the CI/CD service principal,
  as today.
