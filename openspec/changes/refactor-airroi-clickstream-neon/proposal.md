## Why

Three sources are still outside the one-pipeline-per-layer layout:
airroi, clickstream and neon (`pipeline-per-layer` spec, "Sources pending
refactor"). Until they move, the spec carries exception lists, they have no
`run_<source>` job (so CI cannot run them), and 15 human-owned dev pipelines
and 6 human-owned dev jobs still own live dev tables. This change finishes the
rollout for all three in one change, in three staged checkpoints.

## What Changes

- **airroi**: bronze ingestion + SCD pipelines merge into
  `bronze--airroi--<target>`; Silver Landing + Silver Normalised merge into
  `silver--airroi--<target>`; the `silver_airroi` wrapper job goes; `run_airroi`
  becomes flat (tasks held directly, as `run_acnc`).
- **clickstream**: the canonical Auto Loader pipeline and the Python SCD
  pipeline merge into `bronze--clickstream--<target>`; the silver pipeline is
  displayed `silver--clickstream--<target>`; new `run_clickstream`.
- **neon**: silver pipeline displayed `silver--neon--<target>`; new `run_neon`
  (Lakeflow Connect ingestion, Python SCD pipeline, silver). Its bronze keeps two
  pipelines (the documented Lakeflow Connect exception).
- **Every source gets a `run_<source>` job** with the `tag_patterns` task from
  `design-pattern-table-tags`, and `verify--bronze--<source>` where missing.
  Mapping entries for the three sources are added to
  `src/common/design_patterns.yml`.
- **Dev ownership fixed** by the same procedure as before: the user deletes the
  human-owned dev pipelines/jobs, stale dev tables are dropped with approval and
  recreated under the CI/CD service principal by the `run_<source>` jobs.
- **Specs**: airroi, clickstream and neon are removed from every "Sources
  pending refactor" list in `pipeline-per-layer` and `silver-normalised`.

## Capabilities

### Modified Capabilities
- `pipeline-per-layer`: airroi, clickstream and neon follow the layout; the pending lists are emptied.
- `silver-normalised`: pending lists emptied (airroi per-source orchestration).

## Model

Sonnet to implement: a repeat of the acnc and ungm/iso/geonames/nsw procedure.
Opus to propose was not needed. Switch to Opus if a clickstream or neon table
move behaves unlike the earlier ones (streaming tables fed by a Lakeflow Connect
or Auto Loader flow).

## Context

Follows `acnc-two-pipelines` and `ungm-iso-geonames-nsw-two-pipelines`
(archived). Procedure: NAMING.md "Removing a pipeline".

## Impact

- **Staged, one checkpoint per source** (see tasks.md): airroi, then clickstream,
  then neon, each with its own migration job, dev/tst/prd verification and a
  user pause. One PR set, not one run.
- **User-gated steps**: deleting emptied pipelines (CI cannot confirm deletion),
  deleting the human-owned dev pipelines/jobs, merging PRs, approving prd.
- **Free Edition**: one workload at a time; runs are serial. The serverless
  daily quota can block runs (hit on 2026-10-21 for the pattern pipelines).
- tst/prd hold no clickstream or neon tables (never ran); airroi's prd tables,
  if any, are inventoried first (tasks 1.1).
- The SQL SCD twins (clickstream SQL SCD pipeline, neon SQL SCD pipeline and
  merge job) stay as exempt reference variants; moving them to the patterns
  bundle is a later change.
