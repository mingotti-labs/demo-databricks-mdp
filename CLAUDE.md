# CLAUDE.md — demo-databricks-mdp

Conventions for AI-assisted development on this Databricks Modern Data Platform.
This file captures platform-specific decisions; general coding standards are in the
global ~/.claude/CLAUDE.md.

## Platform context

- Databricks Free Edition (serverless compute only, single workspace)
- AWS-hosted workspace: https://dbc-e3197e2d-933b.cloud.databricks.com
- Unity Catalog: one metastore, environments separated by catalog

## Catalog & schema structure

Catalogs: `mdp_dev`, `mdp_tst`, `mdp_prd`

| Layer | Schema pattern | Purpose |
|---|---|---|
| Bronze | `bronze_<source>` | Raw ingestion, append-only |
| Bronze history | `bronze_<source>_history` | Full change history, CDC replay safety net |
| Bronze publish | `bronze_<source>_publish` | Validated bronze, safe for downstream reads |
| Silver | `silver_<domain>` | Conformed, domain-modelled (domains TBD) |
| Gold | `gold_analytics_gateway` | BI / reporting consumers |
| Gold | `gold_integration_gateway` | Operational / API consumers |
| Gold | `gold_ai_gateway` | ML and GenAI consumers |

Always use 3-part names: `catalog.schema.table`. Never use bare or 2-part references.

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
- `src/layers/{bronze,silver,gold}/<source-or-domain-or-gateway>/`: mirrors the catalog/schema naming below, not the ingestion pattern or use case.
- `src/common/`: the only part of `src/` that is plainly importable, wheel-packaged Python.
- `src/seed_data/`: synthetic-data generation notebooks (e.g. `seed_neon_ecommerce.py`) — not a medallion layer, not deployed data, just a way to populate a source system for demo/dev purposes.
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

## Guardrails — never do without explicit confirmation

- No classic clusters — serverless only
- No account-level API calls (Free Edition scope is workspace-level only)
- No `%run` — use proper imports from `src/`
- No `%pip install` in notebooks — declare dependencies in bundle config
- No hardcoded secrets or connection strings — always `dbutils.secrets.get()`
- No destructive DDL (`DROP TABLE`, `TRUNCATE`, `DELETE`) without explicit user approval
- No direct writes to `mdp_prd` catalog from ad-hoc notebooks
