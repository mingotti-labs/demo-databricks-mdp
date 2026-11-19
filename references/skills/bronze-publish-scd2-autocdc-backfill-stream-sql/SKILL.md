---
name: bronze-publish-scd2-autocdc-backfill-stream-sql
description: Writes the Lakeflow pipeline .sql file that moves a legacy SCD type 2 table (with start/end date columns) into a pipeline-owned SCD2 streaming table with its history, then keeps it current from an append-only Delta table that has no change timestamp, using its change data feed. Use when the live source only gets new rows appended (never updated in place).
---

# SCD2 migration with history, live source = append-only table

Two flows into one target: a once-only `AUTO CDC ONCE` backfill streaming the legacy table (each
version at its start date, a retired asset deleted at its end date), and a streaming `AUTO CDC` over
the source's change feed, ordered by `_commit_timestamp`. Tested in dev by the notebook
`references/patterns/src/bronze_publish/bronze_publish_scd2_autocdc_backfill_stream_sql.py`.

## Inputs (ask for any that are missing; never guess)

| Placeholder | Meaning | Example |
|---|---|---|
| `{{target}}` | new SCD2 table, unqualified (the pipeline's catalog and schema) | `asset_dim_migrated` |
| `{{legacy_table}}` | legacy SCD2 table, 3-part name | `main.dw.asset_dim_legacy` |
| `{{source_table}}` | live append-only Delta table, 3-part name, change data feed on | `main.dw.asset_source` |
| `{{keys}}` | business key column(s), comma-separated | `asset_id` |
| `{{columns}}` | key and tracked columns, comma-separated, same names in both tables | `asset_id, asset_name, asset_owner` |
| `{{start_col}}`, `{{end_col}}` | legacy validity columns (DATE or TIMESTAMP; end NULL = open) | `start_date`, `end_date` |

Derived:
- `{{l_columns}}` = each column of `{{columns}}` prefixed with `l.`
- `{{e_columns}}` = each column prefixed with `e.`
- `{{struct_columns}}` = for each column `c`: `'c', l.c` (comma-separated)
- `{{key_join}}` = for each key `k`: `l.k = last.k`, joined by ` AND `

## Steps

1. Collect the inputs; confirm the source is append-only (otherwise use
   `bronze-publish-scd2-autocdc-backfill-snapshot-sql`).
2. Read `assets/template.sql`; replace every placeholder; change nothing else.
3. Write the file as `{{target}}.sql` (or where the user says) and print the "Before you run" notes.
   Only for an unclear request, read `references/examples.md`.

## Before you run (print these)

- Turn the change feed on first: `ALTER TABLE {{source_table}} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)`.
  Rows appended before that are not in the feed.
- The legacy table needs at most one row per key and start date.
- `AUTO CDC ONCE` needs a streaming source (`STREAM(...)`); a batch view is refused.
- An appended row equal to the open version opens no new version.
