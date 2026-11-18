## Context

An engagement has an SCD2 dimension (`asset_dim`: one row per version, `start_date`,
`end_date`) kept by hand-written code. It must become a pipeline-owned SCD2 table fed by a
live source, keeping all history. The patterns bundle (`references/patterns/`) holds
dev-only reference implementations; its schemas are `pattern_bronze` and
`pattern_bronze_publish` (iac).

## Goals / Non-Goals

**Goals:** history and live changes in one SCD2 table; no stage table; the history load
runs once and never again on a normal update; one notebook, numbered steps, runnable in
another workspace by changing two widgets.

**Non-Goals:** the main bundle, CI runs, prd; a source that updates rows in place (see D6).

## Decisions

### D1. One notebook creates everything, including the pipeline file and the pipeline
The user asked for every step in one notebook so it can be replicated. The notebook writes
`dim_asset_migrated.sql` into `<notebook folder>/transformations/` (workspace file) and
creates the pipeline with `WorkspaceClient().pipelines.create(...)`: serverless,
`catalog`/`schema` from the widgets, one `glob` library on that folder. Step 55 looks the
pipeline up by name first, so the notebook can be re-run. The SQL text lives once, in the
notebook, and is shown in the notebook.
Rejected: a bundle pipeline resource plus a separate `.sql` file (two places to copy, and a
bundle deploy to replicate).

### D2. The history is loaded as change events, sequenced by `start_date`
`asset_history` turns each old version into one change event:
`asset_id, asset_name, asset_owner, CAST(start_date AS TIMESTAMP) AS change_ts`.
Auto CDC SCD2 then rebuilds the history itself: `__START_AT` = the version's `start_date`,
`__END_AT` = the next version's `start_date`, the last version open. The old `end_date` is
not copied; it is implied by the next version.
- A version closed with no successor (a retired asset) also emits a delete event at its
  `end_date` (`is_delete = true`), applied with `APPLY AS DELETE WHEN is_delete`, so the
  migrated version is closed too.
- If the old table's `end_date` is not the next `start_date` (for example the day before),
  `__END_AT` will differ from it. Step 80 reports such rows; the engagement decides whether
  that is acceptable.
Rejected: `INSERT INTO ONCE` with `__START_AT`/`__END_AT` copied directly (an append flow
writing into an Auto CDC target bypasses the flow's state; not documented as supported);
`AUTO CDC ONCE ... FROM SNAPSHOT` (one snapshot holds only current values, history lost).

### D3. Flows in `dim_asset_migrated.sql`
```sql
CREATE TEMPORARY VIEW asset_history AS ...;           -- batch read of asset_dim (D2)
CREATE TEMPORARY VIEW asset_live AS
  SELECT asset_id, asset_name, asset_owner, updated_at AS change_ts, false AS is_delete
  FROM STREAM(asset_source);
CREATE OR REFRESH STREAMING TABLE dim_asset_migrated;
CREATE FLOW load_history AS AUTO CDC ONCE INTO dim_asset_migrated
  FROM asset_history KEYS (asset_id) APPLY AS DELETE WHEN is_delete
  SEQUENCE BY change_ts COLUMNS * EXCEPT (is_delete) STORED AS SCD TYPE 2;
CREATE FLOW load_live AS AUTO CDC INTO dim_asset_migrated
  FROM STREAM(asset_live) KEYS (asset_id) APPLY AS DELETE WHEN is_delete
  SEQUENCE BY change_ts COLUMNS * EXCEPT (is_delete) STORED AS SCD TYPE 2;
```
Both flows share the key, the sequence column and its type (`TIMESTAMP`), as Auto CDC
requires for flows on one target. The skill reference documents `AUTO CDC ONCE` for the
snapshot form only, so probe P1 proves this exact form first. Fallback if SQL refuses it:
`dim_asset_migrated.py` with `dp.create_auto_cdc_flow(..., once=True)` for the history and
the same streaming flow; the pattern ID then ends `_python`.

### D4. Names and place
Pattern ID `bronze_publish_scd2_autocdc_history_migration_sql`, notebook named after it in
`references/patterns/src/bronze_publish/`. All tables in one schema (widget `schema`,
default `pattern_bronze_publish`): the user asked for "the patterns schema", and one schema
keeps replication to one setting. Pipeline display name
`bronze--pattern--publish--scd2--history-migration--sql--dev`. Table names as the user gave
them (`asset_dim`, `asset_source`, `dim_asset_migrated`); the NAMING.md rule that pattern
tables are named after the pattern ID is waived here because the names are the
engagement's.

### D5. What step 80 checks
- **History flow did not run again**: in `event_log(<pipeline id>)`, the second update has
  no `flow_progress` event with `rows_written > 0` for `load_history`, and the rows whose
  `__START_AT` came from `asset_dim` are identical before and after (count and a hash over
  all columns, saved in a Python variable after step 55).
- **New changes added**: every step-60 row is a version in `dim_asset_migrated` with
  `__START_AT = updated_at`, and the version it replaced now has `__END_AT = updated_at`.
- Prints a pass/fail line per check and fails the cell (`assert`) on any failure.
- A full refresh resets the once-only flow and reloads the history; that is expected and
  stated in the notebook, not checked.

### D6. The live source is append-only
`asset_source` gets one new row per change, which a streaming read needs. A real source
that updates rows in place needs a change feed (Delta `readChangeFeed`) or a snapshot
flow; the notebook says so in step 15.

### D7. Seed data
Small and fixed (no Faker), so the expected result is readable in the notebook:
- `asset_dim`: 4 assets, 2 to 3 versions each, 2024 to 2025 dates; one asset retired
  (last version closed, no successor).
- `asset_source` (step 20): one change per open asset dated after its last history version.
- Step 60: a second change for two assets and one new asset.

## Probes

- **P1** (before writing the notebook): a minimal pipeline in dev with D3's two flows on
  three rows; proves `AUTO CDC ONCE` from a batch view in SQL, two Auto CDC flows on one
  target, and that the second update skips `load_history`. Scripts and output in
  `references/poc/scd2-history-migration/`, row in `references/docs/registers/probes.md`.

## Risks / Trade-offs

- [P1 fails in SQL] -> the Python fallback in D3; the rest of the design is unchanged.
- [Table quota at the stop line] -> re-read before the first run; step 90 frees the slots.
- [Pipeline owned by a human] -> dev only and disposable, like the rest of the patterns bundle.
