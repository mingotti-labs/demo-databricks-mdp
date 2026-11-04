## Why

The table quota is at 483 of 500 (quota API, 2026-11-04; stop line 488), and the next
stories (market climate, inflation/deflation) need new silver and gold tables. A read-only
scan (`references/poc/table-cleanup/`) found no orphaned tables: every slot is held by
something the bundle defines. neon (9 slots) and clickstream (about 7) are dev-only, feed
no story, and are kept only as working examples of Lakeflow Connect and Auto Loader. The
user wants them kept as deployable references, not backups: moving them to the dev-only
patterns bundle (`references/patterns/`) keeps the code deployable and costs slots only
while someone deploys them to look.

## What Changes

- **neon to the patterns bundle**: the Lakeflow Connect query-based pipeline (PostgreSQL
  through the UC connection `neon_dev`) becomes pattern `bronze_lakeflow_query_postgresql`
  (renamed from `bronze_lakeflow_query`), writing `pattern_bronze.lakeflow_query_postgresql_<table>`
  for the same four tables. The seed job and the two neon verification notebooks move with it.
- **clickstream to the patterns bundle**: the canonical Auto Loader pipeline becomes the
  eighth variant, `pattern_bronze_autoloader_add_new_columns_python`, next to the seven
  already there, writing `pattern_bronze.autoloader_add_new_columns_python`. The event
  generator job and the three clickstream verification notebooks move with it.
- **Not moved** (the pattern is already live elsewhere): clickstream's Python SCD1
  (`bronze_publish_scd1_autocdc_stream_python`, used by yahoo, rba, fred) and its Silver
  Landing (`silver_landing_change_feed_python`, used by every source). Git history keeps the files.
- **Existing patterns repointed**: the three patterns that read `bronze_neon.customers_raw`
  or `bronze_clickstream.web_events_raw` read the new pattern tables, so the patterns bundle
  no longer depends on the main bundle.
- **Main bundle loses**: pipelines `neon_ecommerce_ingestion`, `clickstream_autoloader`,
  `silver_landing_clickstream`; jobs `run_neon`, `seed_neon_ecommerce`, `run_clickstream`,
  `generate_clickstream_events`, `verify_clickstream_pattern` (both edition sources); their
  entries in `src/common/design_patterns.yml` and `verification/`.
- **CI**: `pr.yml` also runs `databricks bundle validate` for the patterns bundle, so its
  code cannot go stale unnoticed.
- **Docs**: `references/patterns/README.md` (new) with how to deploy, run, look and remove
  each pattern; registers, `data-sources.md`, CLAUDE.md "Sources", the two source specs.
- **Stays in iac** (no table slots): volume `bronze_clickstream.s3_clickstream_raw` (all
  eight Auto Loader variants read it), connection `neon_dev`, secret scope `neon-postgres`,
  the four bronze_neon/bronze_clickstream schemas.

## Capabilities

### New Capabilities
- `pattern-sources`: neon and clickstream as deployable reference patterns, with deploy
  instructions and a CI validate step.

### Modified Capabilities
- `pipeline-per-layer`: neon and clickstream are no longer sources of the main bundle.
- `neon-ecommerce-ingestion`: removed; replaced by `pattern-sources`.
- `clickstream-autoloader-ingestion`: removed; replaced by `pattern-sources` (the variant
  write-ups stay in the pattern files).

## Impact

- Frees about 16 dev slots (to about 467). No prd change: neither source is in prd.
- While a pattern is deployed and run: neon 8 slots, clickstream 2, plus event logs.
- The user deletes the three dev pipelines by hand before the implementation PR merges
  (CI cannot confirm a pipeline delete); the clickstream tables left behind are dropped
  with approval. Deleting the Lakeflow Connect pipeline drops its tables.
- CI: no unit runs (neon and clickstream are `ci_auto_run: false`).

## Cross-repo dependencies

None. iac keeps the volume, connection, secret scope and schemas. Dropping the then-empty
`bronze_neon`, `bronze_neon_publish` and `bronze_clickstream_publish` schemas is a later iac
choice (schema slots, not table slots).

## Model

Sonnet: moving files and resources between two bundles, following this design.
