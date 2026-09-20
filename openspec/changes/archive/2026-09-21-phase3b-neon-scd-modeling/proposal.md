## Why

Following `phase3b-bronze-schema-simplification`'s removal of `bronze_neon_history`,
full change history is now modeled as SCD tables in `bronze_neon_publish`
instead. This builds that modeling layer — SCD1 for all four Neon tables,
SCD2 for `customers`/`products` (the two genuinely dimension-like ones) — in
both Python and SQL, per direct instruction, for interview-prep/reference
value as well as real functionality.

## What Changes

- Python: `create_auto_cdc_from_snapshot_flow` (snapshot-comparison Auto CDC)
  for all six SCD flows, reading a batch snapshot of each `bronze_neon.*_raw`
  table. **Not** streaming Auto CDC (`create_auto_cdc_flow`) — a real attempt
  at that failed with `DELTA_SOURCE_TABLE_IGNORE_CHANGES`, since
  `bronze_neon.*_raw` is upsert-maintained (Lakeflow Connect merges changed
  rows in place via `cursor_columns`), not append-only. `skipChangeCommits`
  was considered and rejected — confirmed via Databricks' own docs that it
  silently drops updated rows rather than surfacing them, which would make
  SCD tracking never actually track anything
- SQL SCD1 (`customers`/`products`/`orders`/`order_items`): a plain
  passthrough materialized view — `bronze_neon.*_raw` already is
  "latest-value-per-key" by construction, so no CDC machinery is needed at
  all for SCD1 in SQL
- SQL SCD2 (`customers`/`products`): a hand-rolled two-phase `MERGE` pattern,
  run as a **job**, not a pipeline — `AUTO CDC INTO` is streaming-only in
  SQL with no snapshot equivalent, so a declarative pipeline dataset cannot
  express this; the classic MERGE-based SCD2 pattern (expire the changed
  row, then insert the new version) is the real SQL-native answer for a
  non-append-only source, confirmed against real, well-established Delta
  Lake documentation

## Capabilities

### New Capabilities
- `neon-scd-modeling`: SCD1/SCD2 modeling of Neon's ingested tables into
  `bronze_neon_publish`, in both Python (declarative pipeline, snapshot-based
  Auto CDC) and SQL (materialized-view passthrough for SCD1, hand-rolled
  MERGE job for SCD2)

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3b-bronze-schema-simplification`
(provides the `bronze_neon_publish` schema this writes into) — already
landed.

## Impact

- Adds 2 new pipeline resources (`neon_scd_modeling_python`,
  `neon_scd_modeling_sql`) and 1 new job resource
  (`neon_scd2_merge_sql`) across `dev`/`tst`/`prd`
- Writes into `bronze_neon_publish` only — no changes to `bronze_neon`,
  `bronze_atlas`, or `bronze_clickstream`
