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
- **P3 (2026-10-22, dev, one-off serverless run of `src/common/keep_timestamps.py`
  on a copy of `silver_normalised_acnc.state` in `pattern_bronze_publish`):** a
  rebuild with unchanged input kept every `transformed_timestamp`; a rebuild
  with one row edited, one removed and one added left 22 rows, 20 with their
  original stamp, a new stamp only on the edited and the added row, and the
  removed row gone.
- **P4 (2026-10-22, dev, throwaway pipeline `probe--landing-change-feed--dev`
  reading the P2 copy with `readChangeFeed`, keeping `insert` and
  `update_postimage`, applied by `create_auto_cdc_flow` on
  `(ABN, scd_valid_from_timestamp)` sequenced by `_commit_version`, stamping
  `current_timestamp()` in the stream):** the first run loaded all 70,813 rows
  (one stamp, correct for an initial load); a second run with no change wrote
  nothing. After one edit applied by the `MERGE`, only the closed and the new
  version (2 rows) got a new `transformed_timestamp`; Landing equals a full read
  of the copy (0 rows missing in either direction) and carries
  `ingested_timestamp` and the end times exactly (0 mismatches). Change data
  feed was enabled on an existing table; the stream starts from its current
  snapshot, so no history of the feed is needed.

## Dev result (2026-10-22)

- `run_acnc` run 1 (154226357301263, 17.4 min, all tasks SUCCESS): `migrate`
  recreated `charity_register_scd2` as a plain table (70,811 rows, equal to the
  backup) and dropped Landing and the 16 Normalised materialized views;
  `scd2_merge` wrote 0 rows; Landing (streaming table) and Normalised (plain
  tables) rebuilt, 70,811 Landing rows, no null timestamps; both verifications
  passed.
- `run_acnc` run 2 (246107832143311, 16.8 min, all tasks SUCCESS): `migrate`
  reported nothing to migrate; `scd2_merge` wrote 0 rows; 0 rows restamped in
  the SCD2, Landing and Normalised tables (`charity_register`, `state`,
  `value_lineage` checked). CKAN had no changes between the runs.
- `charity_register_scd2_backup` is kept in dev until dropped by hand.

## Prd result (2026-10-22)

- Main run 39850661171 (#88), 43 min, all SUCCESS. It ran all five units, not
  only acnc: #88 changed `src/common/design_patterns.py`, which every unit's
  `tag_patterns` task uses. `run_acnc` took 17 min, including `migrate` and
  both verifications.
- Not yet checked in prd: rows restamped by a second run, and the SCD2 row
  count against `charity_register_scd2_backup`. The prd backup is kept until
  then.

## Under review: back to standard Auto CDC (probes P5 to P8)

D2 (job `MERGE`) and D4 (notebook rebuild) move tables out of the pipelines
and add our own code: a drift from declarative pipelines. Root cause of the
original rewrite, from the Databricks CDC docs: changes in columns not
tracked for history "overwrite the current row instead of creating a new
version". acnc passed `ingested_timestamp`, new on every reload, into the
snapshot as an untracked column, so every current row was overwritten each
run. The cause was that column, not snapshot Auto CDC.

Direction agreed with the user (2026-10-23), to be proven before acnc changes:
- Bronze publish uses standard `create_auto_cdc_from_snapshot_flow`. Any raw
  column whose value changes on every load (today `ingested_timestamp`) is
  left out of the snapshot. Bronze publish does not care where a column came
  from. `ingested_timestamp` stays in raw only.
- "When was this version first ingested" is `__START_AT`, already renamed
  `scd_valid_from_timestamp` in Silver Landing; "when was it last changed in
  bronze" is `coalesce(__END_AT, __START_AT)`. No extra column.
- Silver Landing reads the SCD2 table's change feed (the docs' supported way
  to stream from an Auto CDC target) and stamps `transformed_timestamp` only
  on the rows it receives, so downstream change feeds carry only real
  changes.
- Silver Normalised: parked until the above is settled. The user is wary of
  a generic parameterised rebuild hiding lineage; it also uses
  `min(ingested_timestamp)` from Landing, which needs another input if
  `ingested_timestamp` leaves Landing.

Probes, on copies in `pattern_bronze_publish`, acnc code untouched:
- **P5** Snapshot Auto CDC from raw without `ingested_timestamp`: two runs
  with unchanged raw; the second writes 0 rows (`DESCRIBE HISTORY`). A
  simulated change closes one version and inserts one.
- **P6** Same flow with a function `source` whose version is raw's fetch time
  (the docs type the version `Any`; their examples use integers): accepted,
  and `__START_AT` equals raw's fetch time.
- **P7** Landing from the P5/P6 table's change feed: after the simulated
  change, only the changed rows arrive and get a new `transformed_timestamp`;
  Landing equals a full read of the SCD2 copy.
- **P8** Streaming Auto CDC (`create_auto_cdc_flow`) from raw, for
  comparison. First check whether raw can be read as a stream at all (it is a
  full reload); if not, record that and stop.

Outcome: if P5 to P7 pass, acnc's bronze goes back to snapshot Auto CDC (a
new migration), the `MERGE` task and `src/common/scd2_merge.py` are retired,
and proposal.md, the spec and NAMING.md are rewritten to match. If not,
record the evidence here and keep D2.

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
