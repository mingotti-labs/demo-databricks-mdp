## Why

Three sources are still outside the one-pipeline-per-layer layout (airroi,
clickstream, neon), and they still carry the old timestamp stamping the bronze
full pattern replaced for acnc, ungm, iso, geonames and nsw_spatial
(`rollout-bronze-full-pattern`). This change finishes both for all three in one
change, in staged checkpoints, and clears the other known debt so that new
sources start on Silver Normalised with one rule and no exceptions:

- the exception lists in `pipeline-per-layer` and `silver-normalised`;
- no `run_<source>` job for the three, so CI cannot run them;
- 15 human-owned dev pipelines and 6 human-owned dev jobs that still own live
  dev tables;
- airroi's Silver Normalised still stamps `current_timestamp()` in a pipeline
  (the parked decision about Silver Normalised timestamps);
- SCD1 tables nothing reads (acnc, ungm, nsw_spatial, neon `customers` and
  `products`), and the stamping `charity_register_valid` still does for acnc's;
- the CKAN HTTP retry (PR #96, branch `fix/ckan-http-retry`, cancelled until a
  change runs acnc);
- ten verification notebooks for these three sources that the generic
  `verify_bronze` job replaces.

What the code shows (2026-10-23):

| Source | Bronze today | Silver Landing today | What it needs |
|---|---|---|---|
| airroi | acnc's bug: raw and the SCD2 views stamp `current_timestamp()`, 2 SCD2 tables | 2 materialized views over SCD2 | The bronze full pattern as is; layout merge; Normalised standard |
| neon | fine: no stamping, snapshot Auto CDC from an upserted Lakeflow Connect raw table, SCD1 x4 and SCD2 x2 | 4 materialized views (2 over SCD2, 2 over SCD1) | Change data feed on, Landing as streaming tables, `run_neon`. Dev only |
| clickstream | SCD1 only, streaming Auto CDC from append-only Auto Loader raw | 1 materialized view over SCD1 | Landing from an SCD1 table's change feed (the one probe) |

## What Changes

Order (user, 2026-10-23): neon, clickstream, airroi, then the clean-up stage
(SCD1 tables and SQL twins moved to the patterns bundle). One
checkpoint after each source: verify, stop, report.

- **One probe first (dev)**: a change feed from an Auto CDC SCD1 target, and
  Landing reading it (clickstream `web_events_scd1`, neon `orders_scd1`). It is
  the only shape not already proven. airroi needs none: it is the same bronze
  full pattern as acnc.
- **Silver Normalised standard**: every normalised source is rebuilt by the
  `normalised` task (acnc's `rebuild.py`, keeping `transformed_timestamp` on
  unchanged rows), so its silver pipeline holds Landing only. airroi moves onto
  it; `src/layers/silver/normalised/pipeline.py` is retired once nothing uses it.
- **neon**: change data feed on its SCD tables; four Landing streaming tables
  over the change feeds; silver pipeline displayed `silver--neon--<target>`;
  `run_neon` (dev only, `ci_auto_run: "false"`: there is no Neon instance in
  prd) with `tag_patterns`. Its bronze keeps two pipelines (the Lakeflow Connect
  exception). The dev human-owned neon pipelines and jobs are deleted by the
  user, the stale dev tables dropped with approval and recreated under the CI/CD
  service principal.
- **clickstream**: the canonical Auto Loader pipeline and the Python SCD
  pipeline merge into `bronze--clickstream--<target>`; Landing becomes a
  streaming table over the SCD1 change feed; silver displayed
  `silver--clickstream--<target>`; `run_clickstream` starts with
  `generate_clickstream_events`. Same dev ownership fix.
- **airroi**: bronze ingestion and SCD pipelines merge into
  `bronze--airroi--<target>`, Landing and Normalised into
  `silver--airroi--<target>` (Landing only; Normalised by the task); the bronze
  full pattern on both SCD2 tables (drop `ingested_timestamp` and the stamping
  from the snapshot, change data feed on); two Landing streaming tables; the
  `silver_airroi` wrapper job goes; `run_airroi` becomes flat.
  `ci_auto_run: "false"` stays (paid API): one dev run, `verify=true`, about
  $0.80. dev has all tables SP-owned; prd has bronze tables only (silver never
  ran there), so prd gets the table-move migration without an API call.
- **Every source** gets the opt-in `verify` gate on its `run_<source>` job, a
  spec file under `verification/bronze_checks/` for the generic `verify_bronze`
  job (replacing the per-source verification jobs and notebooks), and mapping
  entries in `src/common/design_patterns.yml`.
- **Reference-only code moves to the patterns bundle** (last stage, can be cut
  without blocking the rest). First the SCD1 tables nothing reads: `charity_register_scd1`, `unspsc_public_scd1`,
  `property_scd1` and neon `customers_scd1`, `products_scd1`. Their live tables
  are dropped in dev and prd (explicit approval), the bronze verification specs
  stop listing them, `charity_register_valid` stops stamping and the guard
  test's exception goes. Still read, so they stay: neon `orders_scd1` and
  `order_items_scd1`, clickstream `web_events_scd1`. Then the SQL twins,
  documented as exempt reference variants until now: neon's SQL SCD pipeline
  and SQL SCD2 merge job, and clickstream's SQL SCD pipeline. neon's `*_sql`
  dev tables were already dropped with the stale set; clickstream's
  `web_events_scd1_sql` is dropped with its stage's approval. After this neon
  has two bronze pipelines (the Lakeflow Connect exception), one silver
  pipeline, `run_neon`, `seed` and `verify` jobs, and the spec's exempt lists
  are empty.
- **CKAN HTTP retry** (#96's change) merges with the acnc-affecting stage.
- **Specs**: the "Sources pending refactor" lists are emptied in
  `pipeline-per-layer` and `silver-normalised`; `platform-timestamps` covers
  SCD1-sourced Landing and the Normalised standard.

## Capabilities

### Modified Capabilities
- `pipeline-per-layer`: airroi, clickstream and neon follow the layout; the pending lists are emptied.
- `silver-normalised`: pending lists emptied; every source's Normalised is built by the rebuild task.
- `platform-timestamps`: SCD1-sourced Landing; the Normalised standard (added requirements).

## Model

Sonnet to implement: a repeat of the acnc and rollout procedures. Switch to
Opus if the probe behaves unlike the earlier ones, or if a clickstream or
neon table move misbehaves (streaming tables fed by Lakeflow Connect or Auto
Loader).

## Context

Follows `acnc-two-pipelines`, `ungm-iso-geonames-nsw-two-pipelines`,
`correct-platform-timestamps` and `rollout-bronze-full-pattern` (archived).
Procedure: NAMING.md "Removing a pipeline".

## Impact

- **Staged, one checkpoint per source**, each with its own migration or reset
  task, dev verification and a pause. Merging a stage runs only the units CI
  selects (`cicd/affected_units.py` against the PR): neon and airroi are
  `ci_auto_run: "false"`; the SCD1 stage touches acnc, ungm and nsw_spatial
  bronze pipelines, so those three units run in prd (check before predicting
  the time). Whether clickstream runs in prd (synthetic data, new tables there)
  is decided at its stage.
- **User-gated steps**: deleting emptied pipelines (CI cannot confirm
  deletion), deleting the human-owned dev pipelines and jobs, merging PRs,
  approving prd, and every drop.
- **Spend**: airroi about $0.80 for its single dev run; a verified prd run would
  be another $0.80, asked for separately.
- **Free Edition**: one workload at a time; runs are serial. The serverless
  daily quota can block runs (hit on 2026-10-21 for the pattern pipelines).
- tst does not exist; prd holds no clickstream or neon tables (never ran).
