## Why

A current engagement must move an existing SCD type 2 dimension, with its full history,
into a Lakeflow pipeline that keeps it as SCD type 2 from then on. The usual approach
copies the history into a stage table first. This pattern skips that: the pipeline
backfills the history once, through a view over the legacy table, and from then on reads
only the live source. The client's live source today is a materialized view with no change
timestamp; the user also wants the append-only variant of the same source (also without a
timestamp) to compare. Each variant is one notebook that can be copied to another
workspace and run step by step.

## What Changes

- **Two notebooks** in `references/patterns/src/bronze_publish/`, each with widgets
  `catalog` (default `mdp_dev`), `schema` (default `pattern_bronze_publish`) and `teardown`
  (default `false`):
  - `bronze_publish_scd2_autocdc_backfill_snapshot_sql.py`: the live source is a
    materialized view; the live flow is a snapshot flow with `WITH VERSION`.
  - `bronze_publish_scd2_autocdc_backfill_stream_sql.py`: the live source is an
    append-only table; the live flow is a streaming flow over its change feed.
- **Steps shared by both notebooks:**
  - **10** create `asset_dim_legacy` (`asset_id`, `asset_name`, `asset_owner`, `start_date`,
    `end_date`): the legacy SCD2 dimension. **25** seed it with history (several versions per
    asset, one asset retired).
  - **30** write `asset_dim_migrated.sql` into a `transformations/` folder named after the
    notebook; the pipeline picks up that folder.
  - **40** in that file, the backfill: a once-only Auto CDC flow from the temporary view
    `asset_history` (reads `asset_dim_legacy`) into `asset_dim_migrated`, `STORED AS SCD TYPE 2`.
  - **55** create the pipeline (serverless, triggered) with the Databricks SDK, or reuse it
    by name, and run it. **70** run it again after step 60.
  - **80** checks: the backfill matches the legacy table row by row; the backfill did not
    run again in the second update; the step-60 changes are in `asset_dim_migrated`.
  - **90** (only when `teardown` is `true`) delete the pipeline, drop the tables and the
    hidden twins.
- **Steps that differ:**

  | Step | Snapshot notebook (materialized view) | Stream notebook (append-only) |
  |---|---|---|
  | 15 | plain table `asset_source_base` (one row per asset) and materialized view `asset_source` over it (`asset_id`, `asset_name`, `asset_owner`) | table `asset_source` (`asset_id`, `asset_name`, `asset_owner`), change data feed on, rows only appended |
  | 20 | seed `asset_source_base`, refresh `asset_source` | append the first rows |
  | 50 | snapshot flow from `asset_live` (reads `asset_source`) `WITH VERSION` = the view's last refresh time | streaming flow from `asset_live` (change feed of `asset_source`), sequenced by `_commit_timestamp` |
  | 60 | update, insert and delete rows in `asset_source_base`, refresh `asset_source` | append new rows |

- **Docs**: two entries in `references/docs/registers/design-patterns.md`; a section in
  `references/patterns/README.md` with both notebooks and a guide to `WITH VERSION`; the
  `design_pattern` tag mapping for `tag_patterns`.

## Capabilities

### New Capabilities
- `pattern-scd2-history-migration`: backfill an SCD2 dimension with its history into a
  pipeline-owned SCD2 table without a stage table, then keep it current from a
  materialized view (snapshot) or an append-only table (stream), one replicable notebook each.

### Modified Capabilities
None.

## Impact

- Dev only, `mdp_dev.pattern_bronze_publish`. No main-bundle change, no CI unit, no prd.
- Table slots while a notebook's tables exist: snapshot notebook 6 (`asset_dim_legacy` 1,
  `asset_source_base` 1, `asset_source` 2, `asset_dim_migrated` 2); stream notebook 4
  (`asset_dim_legacy` 1, `asset_source` 1, `asset_dim_migrated` 2). Temporary views take no
  slot; the pipelines get no Unity Catalog event log (the notebooks read
  `event_log(<pipeline id>)`).
- Both notebooks use the engagement's table names in one schema, so only one notebook's
  tables exist at a time: run step 90 before switching.
- The quota was 488 to 496 of 500 on 2026-11-10 (stop line 488): re-read it before the
  first run; a clean-up may be needed first. Step 90 gives the slots back.
- Each pipeline is created by its notebook, so it belongs to whoever runs it (a human in
  dev). This matches the patterns bundle, which humans deploy; the main-bundle
  service-principal rule does not apply.

## Cross-repo dependencies

None. The schema `pattern_bronze_publish` already exists (iac, dev only).

## Model

Opus: three probes (P1 to P3 in design.md) must prove SQL forms the docs do not show, and
each may need its fallback.
