---
name: bronze-publish-scd2-autocdc-backfill-snapshot-sid-keyed-sql
description: Writes the Lakeflow pipeline .sql file and a view .sql file that move a legacy SCD type 2 table with a surrogate key column into a pipeline-owned SCD2 streaming table with its history, keep it current from a materialized view without timestamp or key, and expose one surrogate key per version (legacy keys kept, new BIGINT keys after the cut-over). Use when the legacy dimension has a surrogate key and no two versions may share a key.
---

# SCD2 migration with history, one surrogate key per version, live source = materialized view

Two files. The pipeline file is the `bronze-publish-scd2-autocdc-backfill-snapshot-sid-sql` pipeline
(live rows reuse the open legacy key or get `xxhash64(row_hash)`). Its stored key repeats when a row
changes back to earlier values, and a pipeline cannot read its own target to avoid that. The view on top
gives one key per version: the legacy key up to the cut-over, `xxhash64(row_hash, __START_AT)` after.
Tested in dev by `references/patterns/src/bronze_publish/bronze_publish_scd2_autocdc_backfill_snapshot_sid_keyed_sql.py`.

## Inputs (ask for any that are missing; never guess)

| Placeholder | Meaning | Example |
|---|---|---|
| `{{target}}` | new SCD2 table, unqualified | `asset_dim_migrated` |
| `{{target_catalog}}`, `{{target_schema}}` | the pipeline's catalog and schema (for the view) | `main`, `dw` |
| `{{legacy_table}}` | legacy SCD2 table, 3-part name | `main.dw.asset_dim_legacy` |
| `{{source_table}}` | live materialized view, 3-part name (has no key column) | `main.dw.asset_source` |
| `{{sid}}` | surrogate key column of the legacy table (BIGINT) | `asset_sid` |
| `{{keys}}` | business key column(s), comma-separated | `asset_id` |
| `{{columns}}` | business key and tracked columns, comma-separated, no `{{sid}}` | `asset_id, asset_name, asset_owner` |
| `{{start_col}}`, `{{end_col}}` | legacy validity columns (DATE or TIMESTAMP; end NULL = open) | `start_date`, `end_date` |
| `{{cutover}}` | the last legacy date (step 3 gives the query) | `2025-05-01` |

Derived:
- `{{source_catalog}}`, `{{source_schema}}`, `{{source_name}}` from `{{source_table}}`
- `{{u_columns}}` = each column of `{{columns}}` prefixed with `u.`; `{{l_columns}}` the same with `l.`
- `{{row_hash}}` = `sha2(concat_ws('|', coalesce(c1, '<null>'), coalesce(c2, '<null>'), ...), 256)` over
  every column of `{{columns}}`, in order (non-text columns: `coalesce(CAST(c AS STRING), '<null>')`)

## Steps

1. Collect the inputs; confirm the source is a materialized view without the key column.
2. Read `assets/template.sql`; replace every placeholder; change nothing else; write `{{target}}.sql`.
3. If `{{cutover}}` is missing, give the user this query to run and wait for the date:
   `SELECT max(d) FROM (SELECT {{start_col}} AS d FROM {{legacy_table}} UNION SELECT {{end_col}} FROM {{legacy_table}})`.
4. Read `assets/view.sql`; replace every placeholder; write `{{target}}_keyed.sql`.
5. Print the "Before you run" notes. Only for an unclear request, read `references/examples.md`.

## Before you run (print these)

- Run the pipeline once, then `{{target}}_keyed.sql` once; consumers read `{{target}}_keyed`, not `{{target}}`.
- The legacy table needs at most one row per key on any date, or the snapshot fails on duplicate keys.
- First update cost: one snapshot per distinct legacy date (about 20 s each on Free Edition).
- The target takes no second flow; a full refresh replays the legacy dates (the view's keys stay the same).
