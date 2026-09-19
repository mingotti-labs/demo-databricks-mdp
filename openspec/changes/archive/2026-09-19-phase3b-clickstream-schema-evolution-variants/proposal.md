## Why

`clickstream-autoloader-ingestion` demonstrated one `cloudFiles.schemaEvolutionMode`
(`addNewColumns`, Python) end-to-end, with real, empirically-confirmed
behavior. To make this pattern useful as an interview-prep/reference
artifact — the second half of what Phase 3b was asked to cover — the other
three modes (`rescue`, `failOnNewColumns`, `none`) need the same treatment,
in both Python and SQL, each independently deployable and documented with
its exact behavior and error/recovery workflow.

## What Changes

- Reorganize the existing canonical pipeline's source into its own folder
  (`src/layers/bronze/clickstream/python_add_new_columns/`) so each variant's
  `libraries` glob is isolated — critical, since multiple pipelines sharing
  one directory would each pick up every sibling's source file and collide
  on duplicate table declarations. The pipeline's resource key
  (`clickstream_autoloader`) is unchanged — only its source path and display
  name moved, a safe in-place update (see design.md)
- Add 3 new Python variants (`rescue`, `failOnNewColumns`, `none`) as
  independently deployable pipeline resources, each targeting its own table
  (`web_events_rescue`, `web_events_fail_on_new_columns`, `web_events_none`)
- Add 4 SQL variants (`addNewColumns`, `rescue`, `failOnNewColumns`, `none`)
  as independently deployable pipeline resources, each targeting its own
  table (`<mode>_sql` suffix), demonstrating the same patterns in SQL
- Every variant's source is documented in-code with its mode's behavior and
  error/recovery workflow — `addNewColumns` documents the confirmed-live
  behavior from `phase3b-clickstream-autoloader`; the other three document
  behavior sourced from Databricks' own docs, explicitly labeled as not
  independently re-verified here
- Only `addNewColumns` (Python, the existing canonical) is ever triggered —
  the other 7 are built, deployed, and validated, not run

## Capabilities

### Modified Capabilities
- `clickstream-autoloader-ingestion`: gains requirements for the 3 additional
  schema-evolution modes and the SQL-language variants, all built and
  deployable but not run as part of standing verification

## Cross-repo dependencies

None beyond what `phase3b-clickstream-autoloader` already depends on.

## Impact

- Adds 7 new pipeline resources (3 Python + 4 SQL) across `dev`/`tst`/`prd`
- Moves (does not delete) the canonical pipeline's source file; its resource
  key, `pipeline_id`, and existing data are unaffected — confirmed via a real
  `bundle deploy` showing "Updated" not "Created" for it
- No impact on `bronze_neon` or any other source system
