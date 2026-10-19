## Why

A source has four pipelines today (bronze ingestion, bronze SCD, Silver
Landing, Silver Normalised) plus wrapper jobs that only chain them
(`silver_acnc`). The split is a convention, not a platform constraint: a
2026-10-19 probe in dev showed one pipeline can publish to two schemas with
fully qualified names, including an Auto CDC snapshot target. One pipeline
per medallion layer halves the resources per source, flattens `run_<unit>`,
and keeps the bronze/silver boundary (and the verification between the two)
intact. acnc goes first; other sources follow the same pattern later.

## What Changes

- **acnc: four pipelines become two, one per layer.** No new pipelines:
  `acnc_charity_register_ingestion` becomes the bronze pipeline (it gains
  `charity_register_valid`/`_scd1`/`_scd2`) and `silver_normalised_acnc`
  becomes the silver pipeline (it gains Landing's `charity_register`).
  Every table keeps its schema and name, written with a fully qualified
  name. Display names: `bronze--acnc--${bundle.target}`,
  `silver--acnc--${bundle.target}`.
- **Existing tables are moved, never rebuilt**, with Databricks' documented
  table move (`ALTER ... SET TBLPROPERTIES("pipelines.pipelineId"=...)`).
  The move must run as the owner and run-as of both pipelines (the CI/CD
  service principal in every environment), so it is a one-off migration
  job, run in each environment before the code change deploys. SCD2
  history must survive.
- **Old pipelines leave the bundle only once they own no tables**:
  `acnc_charity_register_scd_modeling` and `silver_landing_acnc`.
- **Unnecessary jobs are deleted**: `silver_acnc` (its pipeline and tag
  tasks move into `run_acnc`, which becomes one flat job).
- **Verify jobs are named by layer**: `verify--<layer>--<source>`.
  `verify_acnc_charity_register` becomes `verify_bronze_acnc`
  (`verify--bronze--acnc`); a new `verify_silver_acnc`
  (`verify--silver--acnc`) replaces acnc's use of the shared
  `verify_silver_normalised` (kept for airroi until it migrates).
- **Probes first**: the first tasks prove, in dev with scratch pipelines,
  what the docs leave open (history across a move, reads inside one graph,
  deleting an emptied pipeline, full-refresh protection). The design is
  confirmed or updated before any acnc resource changes.
- Docs: NAMING.md (one pipeline per layer; removing a pipeline; verify job
  names), CLAUDE.md (acnc entry), `ci/affected_units.py` docstring example.

## Capabilities

### New Capabilities
- `pipeline-per-layer`: one pipeline per medallion layer per source, how
  existing tables move into it without data loss, when a pipeline may be
  removed, and job layout (no wrapper jobs, verify jobs by layer).

### Modified Capabilities
- `acnc-charity-register-ingestion`: the SCD tables are built by the bronze
  pipeline, not a separate SCD pipeline; the verification job is
  `verify_bronze_acnc`.

## Model

Opus to propose and to implement: the probes and a data migration run in
`prd` are not a pattern repeat (first table move in this repo, unknowns the
docs do not cover).

## Impact

- acnc resources in all three environments: two pipelines removed, two
  changed, one job removed, one job renamed (recreated), one job added, one
  temporary migration job added then removed.
- Three tables re-homed per environment: `bronze_acnc_publish`
  `charity_register_scd1`/`_scd2`, `silver_landing_acnc.charity_register`.
- Implementation lands as two PRs (migration job, then the consolidation),
  with migration runs in dev, tst, prd between them.
- No change to table names, schemas, grants or the iac repo.
