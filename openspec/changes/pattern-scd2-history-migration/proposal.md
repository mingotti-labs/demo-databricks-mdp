## Why

A current engagement must move an existing SCD type 2 dimension, with its full history,
into a Lakeflow pipeline that keeps it as SCD type 2 from then on. The usual approach
copies the history into a stage table first. This pattern skips that: the pipeline reads
the old dimension once, through a view, and then only reads the live source. The user
wants it as one notebook that can be copied to another workspace and run step by step.

## What Changes

- **New pattern** `bronze_publish_scd2_autocdc_history_migration_sql`: one notebook,
  `references/patterns/src/bronze_publish/bronze_publish_scd2_autocdc_history_migration_sql.py`,
  with widgets `catalog` (default `mdp_dev`) and `schema` (default `pattern_bronze_publish`).
  Its numbered steps:
  - **10** create `asset_dim` (`asset_id`, `asset_name`, `asset_owner`, `start_date`,
    `end_date`): the old SCD2 dimension.
  - **15** create `asset_source`: a simulated live source, one row per change
    (`asset_id`, `asset_name`, `asset_owner`, `updated_at`), append-only.
  - **20** seed `asset_source`; **25** seed `asset_dim` with history (several versions per
    asset, one asset closed).
  - **30** write `dim_asset_migrated.sql` into a `transformations/` folder next to the
    notebook; the pipeline picks up that folder.
  - **40** in that file, a once-only Auto CDC flow loads the history into
    `dim_asset_migrated` from the temporary view `asset_history` (reads `asset_dim`).
  - **50** in the same file, a streaming Auto CDC flow loads live changes from the
    temporary view `asset_live` (reads `asset_source` as a stream).
    `dim_asset_migrated` is `STORED AS SCD TYPE 2`.
  - **55** create the pipeline (serverless, triggered) with the Databricks SDK, or reuse
    it by name, and run it.
  - **60** seed new changes into `asset_source`; **70** run the pipeline again.
  - **80** check: (1) the history flow did not run in the second update and the history
    rows are unchanged; (2) every new change from step 60 is in `dim_asset_migrated`,
    with the version it replaces closed.
  - **90** (off unless the `teardown` widget is `true`) delete the pipeline and drop the
    tables and their hidden twins.
- **Docs**: an entry in `references/docs/registers/design-patterns.md`, a section in
  `references/patterns/README.md`, the `design_pattern` tag mapping for `tag_patterns`.

## Capabilities

### New Capabilities
- `pattern-scd2-history-migration`: move an SCD2 dimension with its history into a
  pipeline-owned SCD2 table without a stage table, in one replicable notebook.

### Modified Capabilities
None.

## Impact

- Dev only, `mdp_dev.pattern_bronze_publish`. No main-bundle change, no CI unit, no prd.
- Table slots while it exists: `asset_dim` 1, `asset_source` 1, `dim_asset_migrated` 2
  (streaming table and its twin) = 4. The views are temporary (no slot); the pipeline gets
  no Unity Catalog event log (the notebook reads `event_log(<pipeline id>)`).
- The quota was 488 to 496 of 500 on 2026-11-10 (stop line 488): re-read it before the
  first run; a clean-up may be needed first. Step 90 gives the 4 slots back.
- The pipeline is created by the notebook, so it belongs to whoever runs the notebook
  (a human in dev). This matches the patterns bundle, which humans deploy; the
  main-bundle service-principal rule does not apply.

## Cross-repo dependencies

None. The schema `pattern_bronze_publish` already exists (iac, dev only).

## Model

Opus: the history flow's SQL form (`AUTO CDC ONCE` from a batch view, next to a streaming
Auto CDC flow on the same target) must be proven by a probe first, and may need the
Python fallback (D3).
