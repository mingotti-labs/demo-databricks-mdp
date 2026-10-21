## Why

Seven of the eight clickstream Auto Loader pipelines exist only to demonstrate
a design pattern (`documented only` in the patterns register). They deploy to
every target, prd included, own no tables, and sit among the live pipelines.
This is change 2 of 3: give pattern-only implementations their own home,
separate from what actually runs.

## What Changes

- **New nested bundle `references/patterns/`**: its own `databricks.yml`
  (bundle `demo-databricks-mdp-patterns`, `dev` target only), `resources/` and
  `src/`. The root bundle cannot reach it: it only includes `resources/**`.
- **Move the seven non-canonical Auto Loader variants** into it: the
  `clickstream_autoloader_{python_rescue,python_fail_on_new_columns,python_none,sql_add_new_columns,sql_rescue,sql_fail_on_new_columns,sql_none}`
  pipelines and their `src/layers/bronze/clickstream/<variant>/` folders. The
  canonical `python_add_new_columns` pipeline stays in the main bundle.
- **Named and grouped by pattern, not by source system.** Resource keys become
  `pattern_<register ID>` (for example `pattern_bronze_autoloader_rescue_python`),
  and the source is grouped by layer, one file per pattern:
  `references/patterns/src/bronze/autoloader_<mode>_<language>.{py,sql}` (later
  `bronze_publish/` and so on). The pipelines demonstrate a pattern; clickstream
  is only the data they happen to read.
- **Root bundle stops syncing `references/`**: `sync.exclude: ["references/**"]`
  in both edition sources of `databricks.yml`, then regenerate. Without it the
  patterns files (and today's docs) still upload to prd.
- **Display name segment `template` becomes `pattern`**
  (`bronze--pattern--autoloader--python--rescue--dev`), matching the "design
  pattern, not template" label. Updated in NAMING.md and CLAUDE.md.
- Register: the seven variants' "Code" locations point at the new bundle.
- **Out of scope**: the SQL twins (`clickstream_publish/sql`, the neon SQL
  SCD1 and `scd2_merge` job) and `hello_world`. Those own tables or are in use;
  moving them needs the iac pattern schemas (change 3), so a later change
  handles them. Also out of scope: CI for the patterns bundle (deployed by hand
  to dev for now) and re-pointing the variants at a pattern schema (change 3).

## Capabilities

### New Capabilities
- `patterns-bundle`: a separate, dev-only bundle for pattern-only
  implementations, isolated from what the main bundle deploys and syncs.

### Modified Capabilities
- `clickstream-autoloader-ingestion`: the variants requirement's deployability
  scenario, since seven of the eight pipelines now deploy from the patterns
  bundle.

## Model

Sonnet to propose and implement. File moves, a small second `databricks.yml`,
and one manual cleanup; the design is settled. Switch to Opus if the nested
bundle misbehaves in an unexpected way.

## Context

Change 2 of 3. Change 3 adds the pattern schemas in `demo-databricks-iac`; the
variants then move off `bronze_clickstream` to them (a one-line change each,
since they hold no data).

## Impact

- **A nested bundle means new resources.** The seven pipelines are deleted from
  the main bundle's deployment and created in the patterns bundle. Moving a
  file does not preserve identity across bundles. They hold no tables (only the
  canonical pipeline's tables exist), so nothing is lost.
- **CI cannot confirm a pipeline deletion** (`bundle deploy` refuses without
  `--auto-approve`; NAMING.md "Removing a pipeline"). The seven pipelines are
  deleted by hand in dev and prd before the implementation PR merges.
- prd stops carrying seven empty pipelines; its pipeline count drops by seven.
- No table, schema or live pipeline changes.
