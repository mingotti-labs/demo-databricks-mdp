## Context

See proposal.md - Why. The procedure and its evidence are in
`openspec/changes/archive/2026-10-20-acnc-two-pipelines/design.md`
(probes P1-P5, option C, the `SHOW TBLPROPERTIES` finding) and NAMING.md,
"Removing a pipeline". Inventory (2026-10-20):

| Source | Ingestion pipeline (destination) | SCD pipeline (deleted) | Tables moved |
|---|---|---|---|
| ungm | `ungm_unspsc_ingestion` | `ungm_unspsc_scd_modeling` | `unspsc_public_scd1`, `_scd2` |
| iso | `iso_country_reference_ingestion` | `iso_country_reference_scd_modeling` | `country_codes_scd2`, `subdivision_codes_scd2` |
| geonames | `geonames_reference_ingestion` | `geonames_reference_scd_modeling` | `country_info_scd2`, `admin1_codes_scd2`, `admin2_codes_scd2`, `cities_scd2` |
| nsw_spatial | `nsw_property_ingestion` | `nsw_property_scd_modeling` | `property_scd1`, `_scd2` |

All ten are streaming tables (Auto CDC snapshot targets). **As found when
the dev migration ran (2026-10-20), this inventory only holds where the
tables exist:** in tst and prd only nsw_spatial's tables exist (ungm, iso
and geonames were deployed there but never run); in dev all ten exist but
belong to the user's identity and to `[dev handsonessential]` pipelines,
not to the service principal's. See D7. The SCD pipelines
have no configuration and glob libraries only; no dataset name collides
with an ingestion dataset. Pipeline-scoped datasets (iso's private
`subdivision_codes_deduped`, the `*_transformed` temporary views) are not
UC objects: redefined in the merged pipeline, not moved.

## Goals / Non-Goals

**Goals:** the four sources fully compliant with `pipeline-per-layer`, no
table rebuilt, SCD2 history intact; a migration job reusable by later
sources.

**Non-Goals:** airroi, clickstream, neon (later changes); Landing data or
silver behaviour (display name only).

## Decisions

### D1. Reuse each ingestion pipeline as the bronze pipeline
Same as acnc D1: destinations exist and have run, keys unchanged, only the
SCD tables move. Libraries gain `- glob: ../../src/layers/bronze/<source>_publish/**`
(all globs, so no `file`/`glob` mix).

### D2. A generic migration notebook and one job with a task per source
`migrations/two_pipelines.py` takes `catalog`, `source_pipeline_id`,
`destination_pipeline_id` and `tables` (comma-separated `schema.table`).
It reads each table's type and owner from the Tables API (not `SHOW
TBLPROPERTIES`), stops the source pipeline, ALTERs the tables not yet
owned by the destination, checks owners and row/closed-version counts
unchanged, then deletes the emptied source pipeline. The job
`migrate_four_sources_two_pipelines` has one task per source chained with
`depends_on` and `run_if: ALL_DONE`: sequential (Free Edition runs one
workload at a time) and a failed source does not block the others.
*Alternative*: copy acnc's notebook four times: four places to fix.

### D7. Environment state found at migration time (amends D2)
- **tst and prd:** the migration notebook skips a listed table that does
  not exist ("nothing to move") and still deletes the emptied SCD pipeline,
  so ungm, iso and geonames only lose their empty SCD pipeline; nsw_spatial
  moves two tables. The first `run_<source>` after PR-B creates the missing
  tables directly in the merged pipeline.
- **dev:** the dev tables of all four sources (bronze raw, SCD, Silver
  Landing) are owned by the user and attached to eight `[dev
  handsonessential]` pipelines, so the SP-run job cannot read them (first
  dev run failed on its first statement, `INSUFFICIENT_PERMISSIONS`, with
  nothing changed). Per the standing rule (human-identity copies are
  disposable) dev is not migrated: the user deletes the eight human
  pipelines, the stale dev tables are dropped (every table has 0 closed
  SCD2 versions, sources are free and re-fetchable), the migration job then
  only deletes the SP's empty SCD pipelines, and the first `run_<source>`
  run in dev creates all tables in the merged layout under the SP.
- A table owned by a pipeline other than the source or the destination
  still fails the run.

### D3. Qualified names and full-refresh protection
SCD streaming tables get `name`/`target` `bronze_<source>_publish.<table>`;
every SCD2 table gets `pipelines.reset.allowed=false` (8 tables). SCD1
tables stay resettable. ungm's and nsw_spatial's flows name their source
`bronze_<source>.<table>_raw`, a two-part name in `source=`; the probes
proved two-part names in `name=` and `spark.read.table`, not in `source=`.
The dev run (task 4.5) is the check; the fallback is the unqualified name,
which resolves to the same dataset through the pipeline's default schema.

### D4. Silver is a display-name change
`silver_landing_<source>` pipelines display as `silver--<source>--<target>`.
They already are the source's only silver pipeline.

### D5. Jobs
- Verify jobs keep their keys, display as `verify--bronze--<source>--<target>`: the four sources here, and also airroi, clickstream and neon (display names only, so no source is left on the old naming).
- `verify_silver_landing` gets job parameters `catalog` and `source`
  (default empty: all sources, today's behaviour); with a source, it checks
  only that source's entities.
- `run_<source>`: bronze pipeline → `run_job` verify bronze → silver
  pipeline → `run_job verify_silver_landing` (`source`). Auto-run (free
  sources). No wrapper jobs exist for these sources.

### D6. Two PRs with migration runs between (as acnc)
PR-A adds the migration job (affects no unit). Run it in dev, tst, prd.
PR-B is the consolidation and removes the migration job. Nothing that
touches these four sources merges in between.

## Risks / Trade-offs

- [Two-part `source=` does not resolve in-graph] → dev run before merge;
  unqualified fallback.
- [prd: four sources' pipelines deleted in one job run] → accepted by the
  user; each task checks counts before deleting and only its own source.
- [CI runs four units after PR-B, lengthening `main.yml`] → once; later
  changes run only what they affect.
- [A stray run of an old SCD pipeline between migration and PR-B] → fails
  on ownership, harmless (acnc P2).
