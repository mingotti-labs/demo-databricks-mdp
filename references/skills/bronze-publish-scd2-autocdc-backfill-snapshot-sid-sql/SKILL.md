---
name: bronze-publish-scd2-autocdc-backfill-snapshot-sid-sql
description: Writes the Lakeflow pipeline .sql file that moves a legacy SCD type 2 table with a surrogate key column (and start/end date columns) into a pipeline-owned SCD2 streaming table with its history and keys, then keeps it current from a materialized view that has no timestamp and no key; live rows reuse the open legacy key or get a new BIGINT key. Use when the legacy dimension has a surrogate key that must survive the migration.
---

# SCD2 migration with history and surrogate key, live source = materialized view

The snapshot pattern (one `AUTO CDC ... FROM SNAPSHOT` flow `WITH VERSION`) with a key column. Both
sides hash the row's own values (`row_hash`, SHA-256 text). A live row reuses the key of the newest
legacy row with the same hash when that row is still open; otherwise its key is `xxhash64(row_hash)`.
Tested in dev by `references/patterns/src/bronze_publish/bronze_publish_scd2_autocdc_backfill_snapshot_sid_sql.py`
(probe P4).

## Inputs (ask for any that are missing; never guess)

| Placeholder | Meaning | Example |
|---|---|---|
| `{{target}}` | new SCD2 table, unqualified (the pipeline's catalog and schema) | `asset_dim_migrated` |
| `{{legacy_table}}` | legacy SCD2 table, 3-part name | `main.dw.asset_dim_legacy` |
| `{{source_table}}` | live materialized view, 3-part name (has no key column) | `main.dw.asset_source` |
| `{{sid}}` | surrogate key column of the legacy table (BIGINT) | `asset_sid` |
| `{{keys}}` | business key column(s), comma-separated | `asset_id` |
| `{{columns}}` | business key and tracked columns, comma-separated, no `{{sid}}` | `asset_id, asset_name, asset_owner` |
| `{{start_col}}`, `{{end_col}}` | legacy validity columns (DATE or TIMESTAMP; end NULL = open) | `start_date`, `end_date` |

Derived:
- `{{source_catalog}}`, `{{source_schema}}`, `{{source_name}}` from `{{source_table}}`
- `{{u_columns}}` = each column of `{{columns}}` prefixed with `u.`; `{{l_columns}}` the same with `l.`
- `{{row_hash}}` = `sha2(concat_ws('|', coalesce(c1, '<null>'), coalesce(c2, '<null>'), ...), 256)` over
  every column of `{{columns}}`, in order (non-text columns: `coalesce(CAST(c AS STRING), '<null>')`)

## Steps

1. Collect the inputs; confirm the source is a materialized view without the key column.
2. Read `assets/template.sql`; replace every placeholder; change nothing else.
3. Write the file as `{{target}}.sql` (or where the user says) and print the "Before you run" notes.
   Only for an unclear request, read `references/examples.md`.

## Before you run (print these)

- Known risk: a row that changes back to its open legacy values, or to values it had after the cut-over,
  gets that earlier key again (one key, two versions). The pipeline cannot read its own target to tell
  (`Graph is not topologically sorted ... cycle`). If no two versions may share a key, use the skill
  `bronze-publish-scd2-autocdc-backfill-snapshot-sid-unique-sql` instead.
- The legacy table needs at most one row per key on any date, or the snapshot fails on duplicate keys.
- First update cost: one snapshot per distinct legacy date (about 20 s each on Free Edition).
- The target takes no second flow; a full refresh replays the legacy dates.
