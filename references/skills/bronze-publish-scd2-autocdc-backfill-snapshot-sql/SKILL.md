---
name: bronze-publish-scd2-autocdc-backfill-snapshot-sql
description: Writes the Lakeflow pipeline .sql file that moves a legacy SCD type 2 table (with start/end date columns) into a pipeline-owned SCD2 streaming table with its history, then keeps it current from a materialized view that has no change timestamp. Use when the live source is a materialized view (full current state per refresh) and the history must keep the legacy dates.
---

# SCD2 migration with history, live source = materialized view

One `AUTO CDC ... FROM SNAPSHOT` flow `WITH VERSION`: one snapshot per legacy date (backfill), then
one per refresh of the view (version = `information_schema.tables.last_altered`). Tested in dev by the
notebook `references/patterns/src/bronze_publish/bronze_publish_scd2_autocdc_backfill_snapshot_sql.py`.

## Inputs (ask for any that are missing; never guess)

| Placeholder | Meaning | Example |
|---|---|---|
| `{{target}}` | new SCD2 table, unqualified (the pipeline's catalog and schema) | `asset_dim_migrated` |
| `{{legacy_table}}` | legacy SCD2 table, 3-part name | `main.dw.asset_dim_legacy` |
| `{{source_table}}` | live materialized view, 3-part name | `main.dw.asset_source` |
| `{{keys}}` | business key column(s), comma-separated | `asset_id` |
| `{{columns}}` | key and tracked columns, comma-separated, same names in both tables | `asset_id, asset_name, asset_owner` |
| `{{start_col}}`, `{{end_col}}` | legacy validity columns (DATE or TIMESTAMP; end NULL = open) | `start_date`, `end_date` |

Derived: `{{source_catalog}}`, `{{source_schema}}`, `{{source_name}}` from `{{source_table}}`;
`{{u_columns}}` = each column of `{{columns}}` prefixed with `u.`.

## Steps

1. Collect the inputs; confirm the source is a materialized view (otherwise use
   `bronze-publish-scd2-autocdc-backfill-stream-sql`).
2. Read `assets/template.sql`; replace every placeholder; change nothing else.
3. Write the file as `{{target}}.sql` (or where the user says) and print the "Before you run" notes.
   Only for an unclear request, read `references/examples.md`.

## Before you run (print these)

- The legacy table needs at most one row per key on any date, or the snapshot fails on duplicate keys.
- First update cost: one snapshot per distinct legacy date (about 20 s each on Free Edition).
- The target takes no second flow; a full refresh replays the legacy dates.
- `current_snapshot_version()` only works in plain subqueries, never inside a `WITH` clause.
