## Why

The design-patterns register says which pattern builds which source, but a
reader looking at a table in Unity Catalog cannot tell what built it. A tag on
the table answers that where the table is. This is change 4 of the
reference/patterns roadmap: tables only (pipelines and jobs are out of scope).

## What Changes

- **New tag `design_pattern = <register ID>`** on every table the live
  pipelines publish, one value per table: the pattern that defines how that
  table is built (for example `bronze_custom_ckan_python` on
  `bronze_acnc.charity_register_raw`, `bronze_publish_scd2_autocdc_snapshot_python`
  on its SCD2 table, `bronze_quarantine_null_key_python` on its quarantine
  table). Every table that uses a pattern carries the tag,
  live or pattern-only.
- **One mapping file**, `src/common/design_patterns.yml`: per source, a default
  pattern per schema plus per-table overrides. It names register IDs only; a
  test fails if an ID is not a heading in the register, or a mapped table does
  not exist in the bundle.
- **One shared tag notebook**, `src/common/tag_design_patterns.py`, modelled on
  `silver/normalised/tag.py`: `ALTER ... SET TAGS` after the refresh, idempotent,
  because `@dp.materialized_view` and `@dp.table` have no tags parameter. It
  runs as a `tag_patterns` task in each `run_<source>` job, after the last
  pipeline task.
- **Pattern tables too**: the seven tables in `pattern_bronze` (dev, patterns
  bundle) are tagged by a `tag_patterns` job in that bundle running the same
  notebook; the pattern ID is `bronze_` plus the table name.
- Silver Normalised tables get the tag from the existing `tag.py` (one extra
  key, `silver_normalised_spec_driven_python`), so no second step for them.
- Register and data-sources docs: a short "Finding a pattern from a table"
  note.

## Capabilities

### Modified Capabilities
- `design-pattern-register`: tables carry their pattern as a Unity Catalog tag.

## Model

Sonnet to propose and implement. It repeats the existing tag step; the only
unknown (tagging streaming tables) is probed first (design.md, P1). Switch to
Opus if the probe shows tags cannot be set on pipeline-owned tables.

## Context

Follows changes 1 to 3 (register, patterns bundle, pattern schemas). Needs no
iac change: tag setting by the table owner needs no grant (confirmed for the
Silver Normalised tags).

## Impact

- Metadata only; no table is recreated or refreshed.
- Each `run_<source>` job gains one short task; a job may hit several
  patterns, so the mapping is per table, not per job.
- Clickstream, neon and airroi get the task when their run jobs land (soon).
