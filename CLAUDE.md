# CLAUDE.md — demo-databricks-mdp

Conventions for AI-assisted development on this Databricks Modern Data Platform.
This file captures platform-specific decisions; general coding standards are in the
global ~/.claude/CLAUDE.md.

## Platform context

- Databricks Free Edition (serverless compute only, single workspace)
- AWS-hosted workspace: https://dbc-e3197e2d-933b.cloud.databricks.com
- Unity Catalog: one metastore, environments separated by catalog

## Naming conventions

@NAMING.md

## Repository structure

Decided in the `phase2-dab-cicd` OpenSpec change (see its design.md for full rationale):

```
demo-databricks-mdp/
  databricks.yml
  resources/
    jobs/
    pipelines/
    dashboards/
    apps/
  src/
    layers/
      bronze/
        neon/
        atlas/
        clickstream/
          python_add_new_columns/   # canonical, only variant ever run
          python_rescue/
          python_fail_on_new_columns/
          python_none/
          sql_add_new_columns/
          sql_rescue/
          sql_fail_on_new_columns/
          sql_none/
      silver/
        <domain>/        # domains TBD, per Phase 4
      gold/
        analytics_gateway/
        integration_gateway/
        ai_gateway/
    common/               # shared importable Python modules (wheel packages, utilities)
    seed_data/            # one-off synthetic-data generators, not part of any medallion layer
  tests/
    common/               # mirrors src/common/ only — NOT src/layers/
  verification/           # live-environment functional checks — see "Verification vs validation"
```

- `resources/<type>/`: grouped by resource kind (job/pipeline/dashboard/app), not one flat directory.
- `src/layers/{bronze,silver,gold}/<source-or-domain-or-gateway>/`: mirrors the catalog/schema naming below, not the ingestion pattern or use case. Exception: `bronze/clickstream/`'s subfolders are one per schema-evolution-mode variant (`python_add_new_columns/`, `sql_rescue/`, etc.) — deliberate, isolating each pipeline's `libraries` glob so pipelines never pick up a sibling variant's source file (see `phase3b-clickstream-schema-evolution-variants`'s design.md). Only `python_add_new_columns` is ever actually run; the other 7 exist as documented, deployable reference material.
- `src/common/`: the only part of `src/` that is plainly importable, wheel-packaged Python.
- `src/seed_data/`: synthetic-data generation notebooks — not a medallion layer, not deployed data, just a way to populate a source system for demo/dev purposes. Two shapes so far: truncate-and-reseed for a database source (`seed_neon_ecommerce.py`) vs. append-a-new-batch for a file-drop source (`generate_clickstream_events.py`) — pick the shape that matches how the real source would behave, not one convention for both.
- `tests/` mirrors `src/common/` 1:1 (standard `databricks bundle init` convention). It does not mirror `src/layers/` — pipeline transformation correctness is validated with inline data-quality expectations and `bundle run --refresh`, not pytest.
- `verification/`: Databricks notebooks that check a *deployed* feature actually works against real/synthetic data (connection liveness, row-count parity, referential integrity), chained into a job per pattern. See CONTRIBUTING.md's "Verification vs validation" section — deliberately distinct from `tests/`.

### Resource type ownership: this repo vs. Terraform

The Databricks Asset Bundle resource schema (`databricks bundle schema`, CLI v1.16.1) defines 35 resource types. Not all of them belong in this repo's `resources/`. Split by who owns them:

**Terraform (`demo-databricks-iac`) owns** — Unity Catalog governance and source-DB infra, same family as what Phase 1 already provisions:
`catalogs`, `schemas`, `external_locations`, `secret_scopes`, `secrets`, `volumes`, and (if Lakebase is adopted later) `database_catalogs`, `database_instances`, `postgres_projects`, `postgres_branches`, `postgres_endpoints`, `postgres_databases`, `postgres_roles`, `postgres_snapshot_schedules`, `postgres_catalogs`.

**Not applicable** — Free Edition is serverless-only (see Guardrails below): `clusters`, `cluster_policies`, `instance_pools`.

**This repo (`demo-databricks-mdp`) owns** — workload resources, added under `resources/<type>/` only when a phase actually needs that type (do not pre-scaffold empty folders):
`jobs`, `job_runs`, `pipelines`, `dashboards`, `apps`, `alerts`, `experiments`, `models`, `registered_models`, `model_serving_endpoints`, `quality_monitors`, `genie_spaces`, `vector_search_endpoints`, `vector_search_indexes`, `sql_warehouses`, `postgres_synced_tables`, `synced_database_tables`.

## DAB targets

Three targets in `databricks.yml`, all pointing to the same workspace,
differentiated by catalog:

- `dev` → `mdp_dev`
- `tst` → `mdp_tst`
- `prd` → `mdp_prd`

## Sources

- **Neon Postgres** (serverless, free tier) — relational source. `bronze_neon` is
  populated by `neon_ecommerce_ingestion`, a query-based Lakeflow Connect pipeline
  (not CDC — the gateway architecture needs classic compute, unavailable on Free
  Edition) reading from the Neon `dev` branch via the `neon_dev` UC Connection
  (`demo-databricks-iac`). `dev`-scoped only: no separate `tst`/`prd` Neon
  branch/instance exists yet, so those targets get this pipeline's code on
  promotion but nothing to actually ingest.
  - Seed data (`src/seed_data/seed_neon_ecommerce.py`) is synthetic, generated with
    `Faker`, not a real dataset.
  - Hard deletes on the Neon source are **not** propagated to `bronze_neon` —
    query-based ingestion without `deletion_condition` can't see them (a deleted
    row just stops appearing in query results). Accepted, not a bug.
  - New columns/removed columns on an already-ingested table are handled by
    Lakeflow Connect automatically (new columns backfill as `NULL` for old rows;
    removed columns are marked `inactive`, not dropped — re-adding a same-named
    column afterward fails the pipeline until a full refresh or a manual drop of
    the inactive column). A **new table** is not auto-ingested — this pipeline
    lists tables explicitly; add a `table:` block and redeploy.
- **MongoDB Atlas** (M0 free cluster) — document source
- **Clickstream files** (synthetic, entirely generated by this repo — no real
  upstream system) — file-drop source. `bronze_clickstream.web_events_raw` is
  populated by `clickstream_autoloader`, a Lakeflow Declarative Pipeline
  Streaming Table using Auto Loader, reading JSON event files from the
  `s3_clickstream_raw` UC Volume (`demo-databricks-iac`,
  `phase3b-clickstream-volume`) at
  `/Volumes/<catalog>/bronze_clickstream/s3_clickstream_raw/web_events/landing/`.
  Multi-env, unlike Neon: `dev`/`tst`/`prd` each generate and ingest their own
  independent synthetic data — there's no single upstream branch to be
  dev-scoped against, since the data is fully synthetic either way.
  - Seed data (`src/seed_data/generate_clickstream_events.py`) is synthetic,
    generated with `Faker`; each run appends a new batch rather than
    truncating/reseeding — files accumulate, matching a real file-drop source.
  - Files are never moved or deleted after ingestion — Auto Loader's
    exactly-once guarantee is checkpoint-based, not file-presence-based.
  - `cloudFiles.schemaEvolutionMode` is set explicitly to `addNewColumns` (Auto
    Loader's own default, made visible rather than implicit). A genuinely new
    column in a later batch terminates the in-flight flow once
    (`"... encountered a schema change during execution and terminated"`), and
    Databricks itself starts and completes a new update automatically (cause
    `SCHEMA_CHANGE`) — confirmed empirically, not assumed. The triggering
    `bundle run`/API call that observed the mid-flight cancellation does exit
    non-zero even though the pipeline self-recovers; don't mistake that for a
    real failure.
  - Interview-prep reference: all four `schemaEvolutionMode` values
    (`addNewColumns`/`rescue`/`failOnNewColumns`/`none`) exist as separate,
    independently deployable pipelines, each in both Python and SQL (8
    total), each with its own target table and an in-code write-up of that
    mode's behavior and error/recovery workflow. Only `addNewColumns`
    (Python, the canonical resource above) is ever actually run — the other
    7 are documented from Databricks' own docs, not independently
    re-verified here. See `src/layers/bronze/clickstream/` and
    `phase3b-clickstream-schema-evolution-variants`'s design.md.

## Development style

- Notebook-first: logic lives in Databricks notebooks (stored as `.py` source files
  in the bundle). Shared utilities go in `src/` as importable Python modules.
- Formatter: `ruff` for all Python (notebooks and scripts).
- Package manager: `uv` (see global CLAUDE.md).

## Workflow

@CONTRIBUTING.md

Non-trivial changes go through OpenSpec first: propose (`openspec change new <name>`),
agree the spec, implement, archive. See `openspec/` and each change's `design.md` for
the decision record behind what's built.

## Operational notes

- **`tst`/`prd` should be deployed via CI/CD (GitHub Actions on merge to
  `main`), not a local human `bundle deploy -t tst|prd`** — once a resource in
  a target has ever been deployed by the CI/CD service principal, a later
  local deploy by a human identity fails on that resource with `403
  PERMISSION_DENIED: Only metastore admins can change pipeline owner`
  (confirmed via a real `tst` deploy attempt against the pre-existing
  `neon_ecommerce_ingestion` pipeline). A target with nothing deployed yet
  (e.g. `prd`, before its first deploy) won't hit this, since there's no
  existing owner to conflict with — but that's an accident of ordering, not a
  reason to keep deploying that target locally afterward.
- **Free Edition's serverless compute pool is small and shared across
  pipelines/warehouses/jobs** — a pipeline run can fail with `RESOURCE_EXHAUSTED:
  You've hit the limit for serverless compute for free usage` even when
  nothing looks busy (`databricks clusters list` empty, all pipelines `IDLE`).
  Check `databricks warehouses list` for a `RUNNING` warehouse sitting idle and
  `databricks warehouses stop <id>` it before retrying — that resolved it in
  practice, confirmed via a real retry.
- **The CI/CD SP's `[dev svc_cicd_github] ...`-prefixed pipeline/job copies
  are the canonical, durable dev data going forward — the
  `[dev handsonessential] ...` (or whichever human deploys locally) copies are
  disposable personal-iteration artifacts.** Confirmed the hard way: an
  earlier cleanup deleted the human-identity dev copy of
  `neon_ecommerce_ingestion`, which (per Databricks' default pipeline-delete
  behavior) dropped `bronze_neon.*_raw` along with it — the Neon Postgres
  source itself was untouched, but the ingested-into-Databricks copy had to be
  rebuilt from scratch. Never treat a human-identity dev pipeline/job's data
  as something worth preserving; if it needs deleting, delete it freely. To
  run something as the SP without local M2M credentials, just trigger the
  SP-owned resource's ID directly (`databricks pipelines start-update
  <pipeline_id>` / `databricks jobs run-now <job_id>`) — execution identity is
  a property of the resource, not the caller. See
  `demo-databricks-iac`'s CLAUDE.md ("CI/CD service principal pipeline
  execution") for the grants this needed to actually work.

## Guardrails — never do without explicit confirmation

- No classic clusters — serverless only
- No account-level API calls (Free Edition scope is workspace-level only)
- No `%run` — use proper imports from `src/`
- No `%pip install` in notebooks — declare dependencies in bundle config
- No hardcoded secrets or connection strings — always `dbutils.secrets.get()`
- No destructive DDL (`DROP TABLE`, `TRUNCATE`, `DELETE`) without explicit user approval
- No direct writes to `mdp_prd` catalog from ad-hoc notebooks
