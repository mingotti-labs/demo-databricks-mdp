## Context

Evidence and measurements are in proposal.md. Draft PR #86 is the silver
experiment (not for merge).

## Decisions

- **D1 Stamp where changes are detected.** `current_timestamp()` only on rows a
  step inserts, modifies or closes; never on a full snapshot.
- **D2 (superseded by D7) Bronze SCD2 via a `MERGE` job task** (pattern
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
- **D6 (superseded by D9) Backfill** of existing SCD2 versions (#88).

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
- Checked 2026-10-23: `charity_register_scd2` equals
  `charity_register_scd2_backup` (72,158 rows, 65,907 current). Only one
  `run_acnc` has run since the migration: its `MERGE` read 65,907 rows and
  wrote 0; Landing and the Normalised tables were created by that run, so all
  their rows carry its stamp. No second run yet, so no restamp count. The prd
  backup is kept.

## Back to standard Auto CDC (probes P5 to P8)

D2 (job `MERGE`) and D4 (notebook rebuild) move tables out of the pipelines
and add our own code: a drift from declarative pipelines. Root cause of the
original rewrite, from the Databricks CDC docs: changes in columns not
tracked for history "overwrite the current row instead of creating a new
version". acnc passed `ingested_timestamp`, new on every reload, into the
snapshot as an untracked column, so every current row was overwritten each
run. The cause was that column, not snapshot Auto CDC.

Direction agreed with the user (2026-10-23), proven before acnc changes:
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

Results (2026-10-23, dev, throwaway pipeline `probe--auto-cdc-snapshot--dev`
on `pattern_bronze_publish.probe_raw`, a copy of `charity_register_raw`):
- **P5 passed.** `probe_p5_scd2`: snapshot Auto CDC from raw with non-null ABN,
  `ingested_timestamp` dropped, no `track_history_except_column_list`. Run 1
  inserted 65,907. Run 2, raw unchanged: 0 rows written (`DESCRIBE HISTORY`).
  Then a simulated reload: a new `ingested_timestamp` on every raw row, one
  charity's name edited, one charity deleted, one fake charity added. Run 3
  inserted 2 and updated 2: the edited charity's old version closed and a new
  one inserted, the deleted one closed, the fake one inserted; 65,907 current.
  With a table as source, `__START_AT` is the pipeline run's time, not raw's
  fetch time.
- **P7 passed.** `probe_p7_landing`: today's Landing code (`land()`, change
  feed of `probe_p5_scd2`, Auto CDC on `(ABN, scd_valid_from_timestamp)`).
  Run 1 loaded 65,907 rows with one stamp; run 2 wrote 0 rows; run 3 wrote the
  same 4 rows, and only those got a new `transformed_timestamp` (65,905 kept
  the first one). Landing equals a full read of `probe_p5_scd2` (0 missing,
  0 extra on key, start and end).
- **P6 passed, with one fix.** `probe_p6_scd2`: same flow, `source` a function
  returning raw without `ingested_timestamp` and, as version, raw's fetch time
  (or `None` when that version is already applied). `__START_AT` equals raw's
  fetch time (65,907 rows at 22:54:10.143). First try looped: the flow applied
  the same snapshot every ~17 s (33 MERGEs of 0 rows, stopped by hand). Cause,
  shown by raising both values: Auto CDC keeps the version to the millisecond
  (`22:54:10.143000`) while raw's fetch time has microseconds
  (`22:54:10.143992`), so raw always looked newer. With the version cut to the
  millisecond (`date_trunc("millisecond", max(ingested_timestamp))`): an
  unchanged run wrote nothing; after a reload with one charity edited, one
  run closed 1 version and inserted 1, both at the new fetch time
  (23:12:13.455).
- **P8 stopped at the first check.** Streaming from raw fails:
  `STREAMING_FROM_MATERIALIZED_VIEW` ("Streaming from Materialized Views is not
  supported"). Raw is a materialized view because it is a full reload, so
  streaming Auto CDC is not an option for acnc.

## Decision (2026-10-23, with the user)

P5 to P7 passed, so acnc's bronze goes back to snapshot Auto CDC. D2 and D6
are superseded; D3 to D5 stay.

- **D7 Bronze full pattern** (pattern
  `bronze_publish_scd2_autocdc_full_load_python`, replacing
  `bronze_publish_scd2_merge_python`). `_raw` is a full load, so its
  `ingested_timestamp` changes on every load and is never part of the
  snapshot. The SCD2 table is a streaming table in the bronze pipeline, built
  by standard `create_auto_cdc_from_snapshot_flow` from a temporary view over
  `charity_register_valid` (raw without NULL-ABN rows) that drops
  `ingested_timestamp` and the `transformed_timestamp` that valid stamps for
  SCD1. Auto CDC versions each snapshot with the pipeline update's time
  (`__START_AT` on inserted versions, `__END_AT` on closed ones). Change data
  feed on, `pipelines.reset.allowed` false. No platform timestamp columns on
  the SCD2 table. P6's function source (exact fetch time as version) was
  dropped: in the real pipeline it fails with
  `REFERENCE_DLT_DATASET_OUTSIDE_QUERY_DEFINITION`, because a function source
  cannot read a dataset defined in its own pipeline. Cost: `__START_AT` is the
  update's time, seconds to minutes after raw's fetch (35 s in dev), not the
  exact fetch time.
- **D8 Silver Landing settles both timestamps.** D3's stream, plus
  `ingested_timestamp = __START_AT`, kept next to `scd_valid_from_timestamp`
  (same value; `ingested_timestamp` is the standard name Normalised reads).
- **D9 New load, no migration** (approved for dev and prd). acnc's SCD2 history
  is not carried over.

## New load (per environment, dev first)

A one-off `reset` task, first in `run_acnc`, replacing #88's `migrate`: if
`charity_register_scd2` is a plain Delta table, drop it,
`charity_register_scd2_backup` and `silver_landing_acnc.charity_register`;
otherwise do nothing. Then the bronze pipeline creates the SCD2 streaming table
from one load and the silver pipeline rebuilds Landing from its change feed.
The Normalised tables are kept; that first run restamps their rows once,
because `ingested_timestamp` changes.

## Risks

- Stale flow state: the bronze pipeline ran a snapshot flow into
  `charity_register_scd2` before #88. Checked in dev: the first run after the
  drop loaded every row.
- Landing's stream must start from the new SCD2 table, not an old checkpoint.
  Checked in dev: Landing equals a full read of the SCD2 table after the first
  run.
- Ownership: the job runs as the CI/CD service principal, which owns the
  dropped tables, as in #88's migration.

## No pipeline retries

A failed update was retried automatically (platform defaults: 5 update and 2
flow attempts), so the first dev run of this change failed over and over on a
code error and spent compute each time. acnc's two pipelines now set
`pipelines.numUpdateRetryAttempts` and `pipelines.maxFlowRetryAttempts` to
`"0"`: an error fails the update once. The other 27 pipelines (20 main, 7
patterns bundle) were changed too, then moved to the rollout change: touching
every pipeline file makes CI run every unit in prd (about 45 min), against
acnc alone (about 17 min; checked with `cicd/affected_units.py`).

## Dev result (2026-10-23, new pattern)

- P6 in the real pipeline failed (see D7). Changed to a snapshot view over
  `charity_register_valid`.
- `run_acnc` run 1: `reset` dropped the old SCD2 table, its backup and Landing;
  the SCD2 table loaded 65,907 rows (all current, one `__START_AT`, 35 s after
  raw's fetch); Landing 65,907 rows, both timestamps populated,
  `ingested_timestamp` = `scd_valid_from_timestamp` on every row, equal to a
  full read of the SCD2 table (0 missing, 0 extra); all tasks SUCCESS.
- `run_acnc` run 2 (raw re-fetched, every row has a new `ingested_timestamp`,
  no business change): the SCD2 table wrote 0 rows, Landing wrote 0 rows, and
  the stamps of Landing and of Normalised (`charity_register`, `state`) were
  unchanged. `verify_silver` was cancelled at the user's request (compute);
  every other task SUCCESS.

## Opt-in verification

The verification tasks cost a serverless start-up each (41 to 47 s for bronze)
and found nothing on repeated runs. `run_acnc` has a job parameter `verify`
(default `"false"`); a condition task (no compute) gates `verify_bronze` and
`verify_silver` on `verify=true`. With verification on, `verify_bronze` runs
after `bronze` and before `silver`; with it off, `silver` runs straight after
`bronze`.

`silver` depends on `bronze` and `verify_bronze` with `run_if: NONE_FAILED`.
The first version used the default `ALL_SUCCESS` (the Databricks docs say an
excluded upstream counts as successful): in prd, with verification off,
`silver` was excluded ("dependency type condition was not met") and so were
`normalised`, `tag` and `tag_patterns`, while the run reported SUCCESS. A failed
verification still stops `silver`; a skipped one does not. Tested in dev with
`verify=false` (run 206238828805026): only `verify_bronze` and `verify_silver`
were excluded and every other task succeeded. The `verify=true` path has not
been run. Because CI runs the job with its defaults, verification is off in
tst/prd runs until the default or the CI command changes.
