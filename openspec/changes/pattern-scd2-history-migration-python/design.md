## Context

`pattern-scd2-history-migration` built the SCD2 migration with history as SQL notebooks
(snapshot, stream, sid, sid_unique) and one skill per notebook. The snapshot family repeats about
50 lines of SQL (temporary views, `FROM SNAPSHOT`, `WITH VERSION`) in three notebooks and three
skill templates. In SQL the views exist only because a snapshot query cannot branch. The user
(2026-11-19) asked for the shared logic in one Python module, with the table-specific part given
as SQL strings.

## Goals / Non-Goals

**Goals:**
- One module holds the version, cut-over, row selection and key logic of the snapshot family.
- Table-specific logic stays SQL, passed as three strings.
- The same results as the SQL notebooks on the same seed data.
- Built in steps: baseline, then `sid`, then one key per version.

**Non-Goals:**
- The stream pattern (later, if the baseline holds up).
- Replacing or removing the SQL notebooks or skills.
- Python functions as inputs (one way only: SQL strings; add later only on a real need).

## Decisions

### D1. Inputs: configuration plus three SQL strings
`migrate_and_load(target, keys, history_sql, live_sql, live_version_sql, technical_columns=(), sid=None)`.
- `history_sql`: the key and tracked columns plus `valid_from`, `valid_to` (TIMESTAMP; NULL =
  open), and the key column when `sid` is set.
- `live_sql`: the same columns without `valid_from`, `valid_to` and the key.
- `live_version_sql`: one row, one orderable value; it changes only when the live data does
  (for a materialized view: `information_schema.tables.last_altered`; if `live_sql` reads several
  tables, the newest of their `last_altered`).
- `migrate_and_load` checks the columns once when the pipeline starts and fails with a message
  naming what is missing.
Alternatives: table names only (rejected: the live logic is often a join or a filter, as the
temporary views were); Python functions (rejected for the baseline: two ways to do one thing).

### D2. Function names follow the SQL views
| SQL | Python |
|---|---|
| `asset_history` | `history()` = `spark.sql(history_sql)` |
| `asset_live` | `live()` = `spark.sql(live_sql)` |
| `asset_versions` | `versions()`: every legacy `valid_from`/`valid_to`, then the live version |
| `asset_cutover` | `cutover()`: the last legacy date |
| `asset_legacy_key` | `legacy_key()` (`sid` only) |
| `asset_union` + `is_live` | none: `snapshot()` picks with an `if` |
| `FROM SNAPSHOT` | `snapshot(last_version)`: `None` when nothing is new, else `(rows, version)` |
| `WITH VERSION` | `next_version(last_version)`: the smallest version after `last_version` |
| flow `migrate_and_load` | `migrate_and_load(...)`: `dp.create_streaming_table` + `dp.create_auto_cdc_from_snapshot_flow(..., stored_as_scd_type=2)` |

`snapshot` returns `history()` rows valid at the version (`valid_from <= v` and `valid_to` NULL
or `> v`) while `v <= cutover()`, else `live()`. Each new function carries a one-line comment
naming the SQL clause it replaces.

### D3. Technical columns
`technical_columns` lists columns that change on every load (load timestamps, batch ids). They
are left out of `row_hash` and passed as `track_history_except_column_list`, so they never open a
version; they still land in the target. The key column (`sid`) is never hashed either.

### D4. Key rule (`sid`) and one key per version
As `..._snapshot_sid_sql` (probe P4): `row_hash` = SHA-256 text of the hashed columns, an empty
value as `<null>`; `legacy_key()` = per `row_hash`, the key of the newest legacy row, only if it
is open; a live row takes it, else `xxhash64(row_hash)`. One key per version as
`..._snapshot_sid_unique_sql`: a view with the stored key up to the cut-over and
`xxhash64(row_hash, __START_AT)` after; the module returns its `CREATE VIEW` text
(`unique_view_sql(...)`) and the notebook runs it once, unless P8 shows the pipeline can publish
the view itself.

### D5. Where the module lives and how a pipeline imports it
`references/patterns/src/common/scd2_migration.py` (patterns bundle). The pipeline file imports
it; P6 proves how (the pipeline's root folder on `sys.path`, or the `sys.path` insert this repo
uses in `unspsc_public_raw.py`). The notebook creates the pipeline with both files.

### D6. One notebook with a `variant` widget
`bronze_publish_scd2_autocdc_backfill_snapshot_python.py`: widgets `catalog`, `schema`,
`teardown`, `variant` (`plain`, `sid`, `sid_unique`). Steps and seed data as the SQL notebook of
that variant; the live source also returns `current_timestamp() AS ingested_timestamp`, named in
`technical_columns`. Step 80 runs the SQL notebook's checks for that variant plus: unchanged rows
opened no version despite `ingested_timestamp`.

### D7. A change to the module reaches every pipeline
Every pipeline using the module picks up a change on its next update; a change to the key or
version rules can open versions in tables that already hold history, which cannot be undone
easily. So: the notebook checks run for every variant before a module change merges, and a
change to those rules is planned as a migration of its own, never a quick fix.

### D8. Skill
`references/skills/bronze-publish-scd2-autocdc-backfill-snapshot-python/` (same layout as the SQL
skills): inputs = the `migrate_and_load` arguments; the template is the pipeline file (import +
call). Checked like the SQL skills: its output runs as-is in a scratch pipeline and equals the
notebook's table.

## Probes

In `references/poc/scd2-history-migration-python/`, rows in `references/docs/registers/probes.md`,
inline rows where possible.
- **P5**: `create_auto_cdc_from_snapshot_flow` with a function source and TIMESTAMP versions;
  first update gives the legacy dates in `__START_AT`/`__END_AT`. Fallback: epoch numbers.
- **P6**: a pipeline file imports `scd2_migration.py` from the bundle. Fallback: the `sys.path`
  insert of `unspsc_public_raw.py`.
- **P7**: `spark.sql(...)` inside the snapshot function during an update.
- **P8** (step 3 only): can the Python pipeline publish the plain view? Fallback: the notebook
  runs the module's `CREATE VIEW` text once.

## Risks / Trade-offs

- [A probe fails] -> its fallback; the module's interface stays.
- [A module change rewrites history] -> D7.
- [Python snapshot functions run on the driver, one per version] -> same cost as SQL (about 20 s
  per version on Free Edition); measured in the notebook run.
- [Table quota near the stop line] -> re-read before each run; step 90 frees the slots.
