# Neon Postgres

Serverless Postgres (free tier) — relational e-commerce source. Not an
API-based source in the REST sense; ingested via Databricks Lakeflow Connect
against a real Postgres connection, not a custom fetch helper.

- `bronze_neon` is populated by `neon_ecommerce_ingestion`, a **query-based**
  Lakeflow Connect pipeline (not CDC — the gateway architecture needs classic
  compute, unavailable on Free Edition) reading from the Neon `dev` branch via
  the `neon_dev` UC Connection (`demo-databricks-iac`).
- `dev`-scoped only: no separate `tst`/`prd` Neon branch/instance exists yet,
  so those targets get this pipeline's code on promotion but nothing to
  actually ingest.
- Seed data (`src/seed_data/seed_neon_ecommerce.py`) is synthetic, generated
  with `Faker`, not a real dataset — truncate-and-reseed shape.
- **Hard deletes are not propagated** to `bronze_neon` — query-based ingestion
  without `deletion_condition` can't see them (a deleted row just stops
  appearing in query results). Accepted, not a bug.
- New columns backfill as `NULL` for old rows automatically; removed columns
  are marked `inactive`, not dropped (re-adding a same-named column afterward
  fails the pipeline until a full refresh or a manual drop of the inactive
  column). A **new table** is not auto-ingested — the pipeline lists tables
  explicitly.

## SCD modeling — Python and SQL, deliberately different mechanisms

`bronze_neon.*_raw` is upsert-maintained (Lakeflow Connect MERGEs changed rows
in place via `cursor_columns`), not append-only — streaming Auto CDC
(`create_auto_cdc_flow`) fails against it with
`DELTA_SOURCE_TABLE_IGNORE_CHANGES` (confirmed via a real run). `skipChangeCommits`
is not a fix — it silently drops the updated rows instead of surfacing them.

- **Python**: `create_auto_cdc_from_snapshot_flow` (snapshot comparison, not
  streaming) against `bronze_neon.*_raw` directly, no intermediate snapshot
  view needed (confirmed via a real run). SCD1 for all four tables, SCD2 for
  `customers`/`products` only.
- **SQL SCD1**: a plain passthrough materialized view — `bronze_neon.*_raw`
  already is "latest value per key" by construction.
- **SQL SCD2**: `AUTO CDC INTO` is streaming-only in SQL with no snapshot
  equivalent, and `MERGE` isn't valid inside a declarative pipeline dataset —
  runs as a **job** (`neon_scd2_merge_sql`), using a classic two-phase
  `MERGE` pattern (expire the old version, insert the new one).

No platform-added `ingested_timestamp`/`transformed_timestamp` columns yet
(introduced later with AirROI — see NAMING.md's "Platform-added timestamp
columns" and `docs/registers/source_systems/airroi.md`). Apply if this source is
revisited.
