## Why

Roadmap Phase 3a: the platform's first ingestion pattern, Lakeflow Connect from
Neon Postgres into `bronze_neon`. The native PostgreSQL CDC connector needs a
gateway (classic compute), which Free Edition doesn't support (confirmed via a real
`clusters create` rejection — "does not have any associated worker environments");
this uses the query-based variant instead — still Lakeflow Connect, just the
architecture pattern that issues periodic queries rather than subscribing to a
change feed, and doesn't need a gateway. True CDC stays scoped to roadmap Phase 3e.
Neon's `dev` branch (from `phase1-neon-branching`) currently has no tables, so this
also seeds it with synthetic e-commerce data first — there's nothing to ingest
otherwise.

## What Changes

- Seed data: `src/seed_data/seed_neon_ecommerce.py` (Faker-generated — customers,
  products, orders, order_items, referential integrity preserved, deterministic via
  a fixed RNG seed) + `resources/jobs/seed_neon_ecommerce.job.yml` (serverless,
  `psycopg2-binary` + `faker` declared via the job's `environments:` block, not
  `%pip install`; manually triggered, truncates and reseeds each run)
- Ingestion pipeline: `resources/pipelines/neon_ecommerce_ingestion.pipeline.yml` —
  query-based, references the `neon_dev` UC Connection (from `iac`), one `table`
  object per source table with `cursor_columns: [updated_at]`, landing in
  `${var.catalog}.bronze_neon`
- No `deletion_condition` — query-based ingestion can't see hard deletes without
  explicit soft-delete tracking on the source; accepted as a known limitation rather
  than adding soft-delete machinery for a use case that doesn't need it yet
- No default schedule — triggered manually (`databricks bundle run`), matching
  `hello_world`'s pattern; add a Jobs `pipeline_task` + cron later if needed
- Scoped to `dev` only — Neon has no separate `tst`/`prd` branch/instance, so
  `tst`/`prd` get this pipeline's code once promoted, but nothing to actually run
  against yet
- A manual walkthrough guide (`docs/lakeflow-connect-manual-guide.md`) mirroring
  these steps through the Databricks UI, for hands-on verification against a
  connector never used before
- Schema evolution documented (not silently assumed): new/removed columns rely on
  Lakeflow Connect's built-in handling; new tables need a manual `table:` block
  added and a redeploy, since this pipeline lists tables explicitly rather than
  ingesting the whole schema — see design.md
- A standing verification suite — `verification/` (Databricks notebooks) +
  `resources/jobs/verify_neon_ecommerce_pattern.job.yml` (chained multi-task job) —
  so the whole pattern (connection liveness, seed data integrity, ingested-row-count
  parity) can be re-checked on demand, not just proven once during implementation

## Capabilities

### New Capabilities
- `neon-ecommerce-ingestion`: the seed data and the query-based ingestion pipeline
  that lands it in `bronze_neon`

### Modified Capabilities
(none)

## Cross-repo dependencies

Depends on `phase3a-neon-uc-connection` in `demo-databricks-iac` — this change's
ingestion pipeline references the `neon_dev` connection that one creates, and its
connectivity must already be verified before this change is applied. Also depends
on the already-archived `phase1-neon-branching` (`dev` branch + `neon-postgres`
secret scope).

## Impact

- Adds a new job (seed) and a new pipeline (ingestion) resource to the bundle
- Writes real (synthetic) data into `mdp_dev.bronze_neon.{customers,products,
  orders,order_items}` once both are run
- No effect on `tst`/`prd` catalogs — see "Scoped to dev only" above
- Uses the `Faker` Python library for all seed data generation (architecture
  component, recorded here per direct request — see design.md)
