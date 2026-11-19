## Why

The SQL patterns of `pattern-scd2-history-migration` (snapshot, sid, sid_unique) copy the same
logic into every notebook and every skill template: how versions are found, the cut-over, which
rows a version reads, the key rule. A fix means editing each copy. The user wants that logic in
one Python module, changed once and used everywhere, while the table-specific part stays as
plain SQL: a compromise between full SQL and full Python.

## What Changes

- **One module** `scd2_migration.py` in the patterns bundle with one entry point:

  ```python
  migrate_and_load(
      target="asset_dim_migrated",
      keys=["asset_id"],
      history_sql="SELECT ..., valid_from, valid_to FROM <legacy>",   # was the view asset_history
      live_sql="SELECT ... FROM <live source>",                        # was the view asset_live
      live_version_sql="SELECT last_altered FROM ...information_schema.tables WHERE ...",
      technical_columns=["ingested_timestamp"],   # optional: not hashed, not tracked
      sid=None,                                   # optional: "asset_sid" turns the key rule on
  )
  ```

  The three SQL strings are the table-specific part: any `SELECT` (joins, filters, renames),
  the same text the temporary views held in the SQL notebooks. Everything else is in the module.
- **Function names follow the SQL views**: `history()`, `live()`, `versions()`, `cutover()`,
  `legacy_key()`, `migrate_and_load()`. Two new small ones replace what `FROM SNAPSHOT` and
  `WITH VERSION` did: `snapshot(last_version)` and `next_version(last_version)`.
  `asset_union` and its `is_live` flag are not needed: `snapshot` picks legacy or live rows
  with an `if`.
- **Technical columns** (`technical_columns`): left out of `row_hash` and out of the history
  tracking (`track_history_except_column_list`), so a load timestamp does not open a version
  on every load; they still land in the target.
- **Built in steps**, each checked in dev before the next:
  1. Baseline: the plain snapshot pattern (no key).
  2. `sid`: the key rule of `..._snapshot_sid_sql` (open legacy key by `row_hash`, else
     `xxhash64(row_hash)`).
  3. One key per version: the `asset_dim_unique` view of `..._snapshot_sid_unique_sql`.
- **One notebook** `bronze_publish_scd2_autocdc_backfill_snapshot_python.py` with a `variant`
  widget (`plain`, `sid`, `sid_unique`): the same seed data, steps and checks as the SQL
  notebooks, plus a check that a technical column opens no version. Its pipeline file is a
  few lines calling `migrate_and_load`.
- **One skill** `bronze-publish-scd2-autocdc-backfill-snapshot-python` that writes that
  pipeline file (the call and its three SQL strings). The SQL skills stay.
- **Docs**: one entry in `design-patterns.md`, a README section, probes in the register.

## Capabilities

### New Capabilities
- `pattern-scd2-history-migration-python`: the snapshot migration (plain, sid, sid_unique) as one
  Python module configured with three SQL strings.

### Modified Capabilities
None.

## Impact

- Dev only, `mdp_dev.pattern_bronze_publish`. No main-bundle change, no CI unit, no prd.
- Table slots while the notebook's tables exist: 8, as the SQL snapshot notebook (plus 1 for the
  `sid_unique` view). Probes use inline rows (about 3 slots each). Re-read the quota first
  (stop line 488); step 90 gives the slots back.
- Risk: a change to the module reaches every pipeline that uses it on its next update; a change
  to the key or version rules can open versions in tables that already hold history (D7).

## Cross-repo dependencies

None.

## Dependencies in this repo

Builds on `pattern-scd2-history-migration` (PRs #203 and #204): the SQL notebooks are the
reference results. Implement after both merge.

## Model

Opus: a new design with three probes (Python snapshot source with timestamp versions, a shared
module imported by a pipeline, `spark.sql` inside the snapshot function).
