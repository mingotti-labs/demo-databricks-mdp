## Why

Free Edition caps each catalog at 50 schemas, and both catalogs were at the
cap (2026-10-30), so no new source could get its schemas. The user decided
to fold the fourteen `silver_landing_<source>` schemas into one
`silver_landing` schema, with tables named `<source>__<entity>` (entity =
today's table name). `demo-databricks-iac`'s `free-silver-landing-schema`
created `silver_landing` (applied 2026-10-30); this change moves every
Landing table into it, so a later iac change can drop the twelve old
schemas (dev and prd then sit near 37 schemas each).

## What Changes

- **Every Landing table is rebuilt as `silver_landing.<source>__<entity>`**:
  the entity files' `create_streaming_table` / `create_auto_cdc_flow` names
  change; each table is refilled by its silver pipeline from the Bronze
  Publish change feed (a new table reads the whole feed). No source fetch is
  needed for the rebuild. The values are the same; `transformed_timestamp` on
  the rebuilt rows is the rebuild time (they are inserted rows).
- **Silver pipelines**: default `schema:` becomes `silver_landing` (probe P1
  first). Resource keys and display names do not change (a key change would
  recreate the pipeline).
- **Readers of Landing**: the Silver Normalised specs (`from:`), the
  spec checker (`src/common/normalised_spec.py`: a source reads only
  `silver_landing.<source>__*`), `profile.py`, `verify_silver_landing.py`,
  `verify_silver_normalised.py`, the `landing:` job parameters and
  `migrations/acnc_reset_scd2.py`.
- **Design-pattern tags**: `design_patterns.yml` lists `silver_landing` per
  source; the tag step tags only that source's tables (`<source>__` prefix)
  in the shared schema.
- **Old tables dropped with the user's approval** (each with its hidden
  `__materialization_mat_*` twin), once the new ones verify: 25 in `mdp_dev`,
  22 in `mdp_prd`. A table removed from a pipeline's code stays in place
  (probes register, `correct-platform-timestamps` P1), so this is a manual step.
- **Folded in (user, 2026-10-30)**: the table and schema quota note in
  CLAUDE.md "Operational notes"; the user deletes the empty human dev
  geonames pipelines `d5259087` (bronze) and `50dcfbf4` (silver).
- **Docs and specs**: NAMING.md (schema table, Landing table names),
  `references/docs/medallion/silver.md`, the registers, the
  `silver-normalised-propose` skill and template, and the baseline specs
  that name a Landing schema.
- Not included: `cicd/databricks/standard.yml` (the standard edition stays on
  one schema per source, as `single_workspace` in iac: the user's decision);
  folding `bronze_<source>_publish` or `silver_normalised_<source>`; dropping
  the old schemas (iac).

## Capabilities

### Modified Capabilities
- `silver-landing`: tables live in `silver_landing`, named
  `<source>__<entity>`.
- `pipeline-per-layer`: the silver pipeline's default schema is
  `silver_landing`.
- `silver-normalised`: a source reads only its own `silver_landing.<source>__*`
  tables.
- `portfolio-internal-data`, `sec-company-facts-ingestion`,
  `wikipedia-sp500-ingestion`, `yahoo-market-data-ingestion`: their Silver
  Landing requirement names the new tables.

## Cross-repo dependencies

- Depends on `free-silver-landing-schema` in `demo-databricks-iac` (applied):
  it created `silver_landing` with the CI/CD grants.
- Provides for a later `demo-databricks-iac` change that drops the twelve
  `silver_landing_<source>` schemas from `free_workspace`; it must wait until
  this change has run in prd and the old tables are dropped.

## Model

Opus to implement: the order of the migration depends on probe P1 (can a
deployed pipeline change its default schema) and on checking each rebuilt
table; the renames themselves are mechanical.

## Impact

- **Runs**: merging changes every silver pipeline and shared code, so CI runs
  every auto-run unit in prd (about 45 minutes, including SEC's and Yahoo's
  fetches). airroi, clickstream and neon are not auto-run; they have no prd
  Landing tables, and in dev they are run by hand.
- **Table quota**: old and new tables coexist until the drop, up to +94 slots
  (dev 25 and prd 22 tables, 2 slots each) on top of 388/500; the drop gives
  them back.
- **Schema quota**: no new schema; the twelve old ones go in the iac follow-up.
- **Drops**: 47 Landing tables in total, with the user's approval; all of
  them are rebuilt from bronze, which is untouched.
