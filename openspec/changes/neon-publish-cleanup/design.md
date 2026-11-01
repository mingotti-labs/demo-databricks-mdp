## Context

Neon is dev-only (`cicd/databricks/free.yml` defines its resources in the `dev`
target; no prd Neon instance exists). Live inventory in `mdp_dev`, 2026-11-01:

| Schema | Objects | Slots | Decision |
|---|---|---|---|
| `bronze_neon` | 4 `*_raw` streaming tables, 4 twins, 1 event log | 9 | keep |
| `bronze_neon_publish` | 4 streaming tables (`customers_scd2`, `products_scd2`, `orders_scd1`, `order_items_scd1`), 4 twins, 1 event log | 9 | remove |
| `silver_landing` | `neon__customers`, `__products`, `__orders`, `__order_items`, 4 twins, 1 event log (`silver--neon--dev`) | 9 | remove |

Neon's code in the repo: `src/layers/bronze/neon_publish/python/` (4 files),
`src/layers/silver/landing/neon/` (4 files), inline resources in both edition
files (pipelines `neon_ecommerce_ingestion`, `neon_scd_modeling_python`,
`silver_landing_neon`; jobs `run_neon`, the seed job), checks files
`verification/{bronze,silver_landing}_checks/neon.yml`. The patterns bundle
(`references/patterns/`) holds `bronze_publish_scd1_autocdc_snapshot_python`,
`bronze_publish_scd1_autocdc_stream_sql`, `bronze_publish_scd1_materialized_view_sql`
and `bronze_publish_scd2_merge_sql`; it lacks the Python snapshot SCD2 flow.

The count is 456 of 500; `silver-domain-investments` adds 36 (dev and prd) and
reaches 492, over the 488 line.

## Goals / Non-Goals

**Goals:**
- Free 18 slots without losing what the project learned: the Python snapshot SCD2
  pattern and its findings survive as a reference, and every removed file can be
  put back from one folder.
- Leave a source that still shows the managed Lakeflow Connect pattern.

**Non-Goals:**
- Removing clickstream, airroi, acnc Silver Normalised or anything else: not
  chosen by the user. This change alone does not make room for gold.
- Changing how any other source runs.

## Decisions

### Keep `bronze_neon` and its pipeline, remove what reads it
The user's choice. The raw tables are the only live example of a managed Lakeflow
Connect query-based ingestion (`bronze_lakeflow_query`); the Publish and Landing
tables show patterns that other sources show too
(`bronze_publish_scd2_autocdc_full_load_python`, `silver_landing_change_feed_python`).
`run_neon` keeps its ingestion task and the bronze verification; its Publish and
Landing tasks go. `design_patterns.yml` keeps `bronze_neon: bronze_lakeflow_query`
and loses the other schemas and the two table entries; with no `silver_landing`
entry for neon, the test that requires a Landing checks file per source no longer
needs `neon.yml`.

### The one pattern only Neon shows: Python snapshot SCD2
Compared against the register and the patterns bundle: the SCD1 snapshot, SQL SCD1
and SQL SCD2 merge variants are in the patterns bundle already. The Python
snapshot SCD2 flow (`create_auto_cdc_from_snapshot_flow` with
`stored_as_scd_type=2` and `track_history_except_column_list` for platform
columns) exists only in Neon's `customers_scd2.py` and `products_scd2.py` as live
code; the register says it is being replaced by the bronze full pattern everywhere
else. It moves to
`references/patterns/src/bronze_publish/bronze_publish_scd2_autocdc_snapshot_python.py`
(source: the dev UNGM codes, as its SCD1 sibling, so it needs no Neon) with a
pipeline resource `pattern_bronze_publish_scd2_autocdc_snapshot_python`
(`bronze--pattern--publish--scd2--snapshot--python--<target>`). It is never run
(the patterns bundle's pipelines are reference only), so it holds no table. The
register entry keeps the three findings (streaming fails with
`DELTA_SOURCE_TABLE_IGNORE_CHANGES`; `skipChangeCommits` drops updated rows;
changing the source of an already-run flow can add duplicate no-op versions) and
points its Code line to the patterns bundle.

### Backup folder, not only git history
`references/backups/neon/`: the removed source files, the two pipelines' inline
YAML and the `run_neon` task list as separate files, the two checks files, and
`RECOVERY.md`: copy the YAML back into the `dev` target of
`cicd/databricks/free.yml` (and `standard.yml`), copy the source files to their
paths, restore the checks files and `design_patterns.yml` entries, regenerate with
`apply_edition.py`, deploy by PR, run `run_neon` (the tables rebuild from
`bronze_neon`; Landing history restarts). Git history holds the same, but a
folder is quicker to find; the main bundle excludes `references/**`, so the files
are never uploaded. Alternative: leave it to git. Rejected by the user (save the
pipelines as backups so recovery is easier).

### Order, because pipeline deletes and drops are the user's
1. The PR merges (the draft deploys to dev first): the bundle no longer defines the
   two pipelines; `bundle deploy` will not delete a pipeline without
   confirmation, so they stay in the workspace, idle.
2. The user deletes the two SP-owned pipelines, `bronze--neon--scd--python--dev`
   and `silver--neon--dev`, and their stale human-owned copies (a deleted
   regular pipeline keeps its tables).
3. With the user's approval, drop the eight tables, their twins and the two
   `event_log_*` tables.
4. Read the quota again: expected 438.

## Risks / Trade-offs

- [The dev Landing history of Neon is lost] → synthetic data, rebuildable from
  `bronze_neon` by restoring the backup; `bronze_neon` is untouched.
- [A removed file is needed by something else] → grep for `neon_publish`,
  `silver_landing/neon` and `neon__` before deleting; the full test suite and
  `databricks bundle validate -t dev` run before every push.
- [18 slots is not enough for gold] → stated openly: after this change and the
  investments domain the count is 474; gold needs a further clean-up chosen by the
  user (clickstream dev copy 6 slots, AirROI 27, ACNC Silver Normalised 34).
- [Hidden twins or event logs left behind keep slots] → the drop step lists them
  by name from `information_schema`, and the quota is read afterwards.

## Migration Plan

1. Merge the proposal.
2. Implementation PR (draft): backup folder and `RECOVERY.md`, the new pattern
   file and resource, the removals, register and docs; `databricks bundle validate`
   for dev and prd, tests, a dev deploy as the service principal; check
   `run_neon` still ingests (`bronze_neon` row counts unchanged).
3. The user deletes the two pipelines; the drops with approval; read the quota.
4. Archive.

Rollback: restore from `references/backups/neon/` as `RECOVERY.md` says.
