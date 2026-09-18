## 1. Pre-flight

- [x] 1.1 Confirm `phase3a-neon-uc-connection` (iac) is applied and its live
      connectivity check passed — re-verified from here via the same mechanism
      (temporary foreign catalog, `SHOW SCHEMAS IN <catalog>`, dropped after):
      returned `public`/`pg_catalog`/`information_schema` again, confirming it's
      still live, not just trusted from the other change

## 2. Seed data

- [x] 2.1 Create `src/seed_data/seed_neon_ecommerce.py`: Faker-seeded (fixed RNG
      seed for reproducibility), creates `customers`/`products`/`orders`/
      `order_items` (each with `updated_at`) if they don't exist, truncates and
      reseeds on every run, connects via the `neon-postgres` secret scope
- [x] 2.2 Create `resources/jobs/seed_neon_ecommerce.job.yml`: serverless, notebook
      task pointing at 2.1, `environments:` block declaring `psycopg2-binary` and
      `faker` (not `%pip install`) — `databricks bundle validate --target dev`
      passed
- [x] 2.3 Deploy and run the seed job — succeeded: `customers=200 products=50
      orders=500 order_items=1240`
- [x] 2.4 Confirm data landed: queried row counts independently through the
      `neon_dev` UC Connection (temporary foreign catalog, dropped after) —
      matched the notebook's own reported counts exactly

## 3. Ingestion pipeline

- [x] 3.1 Create `resources/pipelines/neon_ecommerce_ingestion.pipeline.yml`:
      `ingestion_definition.connection_name = neon_dev`, one `table` object per
      source table (`source_catalog: app`, `source_schema: public`,
      `table_configuration.query_based_connector_config.cursor_columns:
      [updated_at]`, `destination_catalog: ${var.catalog}`,
      `destination_schema: bronze_neon`) — `databricks bundle validate --target
      dev` passed on the first attempt (JSON shape grounded in the real docs
      example fetched earlier, not the cached CDC-shaped skill reference)
- [x] 3.2 Deploy — `databricks bundle deploy --target dev` created the pipeline
      with no errors
- [x] 3.3 Run — succeeded on the first real run: all four flows
      (`customers`/`products`/`orders`/`order_items` `_upsert`) completed
- [x] 3.4 Confirm landed data: queried `mdp_dev.bronze_neon.{customers,products,
      orders,order_items}` — row counts exactly match the seed data (200/50/500/
      1240)

## 4. Manual walkthrough guide

- [x] 4.1 Write `docs/lakeflow-connect-manual-guide.md`: mirrors the UI-driven
      equivalent of the connection + pipeline setup (Catalog Explorer > External
      Data > Connections, then Jobs & Pipelines > Create > ETL Pipeline), including
      the two real gotchas hit while building the automated version (`sslmode` not
      supported, `SHOW SCHEMAS IN CONNECTION` not valid syntax — use a temporary
      foreign catalog instead) and the schema-evolution behavior from design.md

## 5. Verification suite

- [x] 5.1 Create `verification/verify_neon_connection.py`: temporary foreign
      catalog on `neon_dev`, asserts `public` is among its schemas, drops the
      temporary catalog
- [x] 5.2 Create `verification/verify_seed_data.py`: asserts all four Neon tables
      have rows, and referential integrity holds
- [x] 5.3 Create `verification/verify_bronze_neon_ingestion.py`: asserts
      `mdp_dev.bronze_neon.*` row counts match the Neon source counts for all four
      tables
- [x] 5.4 Create `resources/jobs/verify_neon_ecommerce_pattern.job.yml`: three
      tasks chained via `depends_on` — `databricks bundle validate --target dev`
      passed
- [x] 5.5 Deploy and run — succeeded end-to-end on the first real run:
      `verify_connection` → `neon_dev connection OK -- schemas:
      ['information_schema', 'pg_catalog', 'public']`; `verify_seed_data` →
      `seed data OK -- {'customers': 200, 'products': 50, 'orders': 500,
      'order_items': 1240}, referential integrity holds`;
      `verify_bronze_ingestion` → `bronze_neon ingestion OK -- {'customers': 200,
      'products': 50, 'orders': 500, 'order_items': 1240}`. This run *is* the
      final proof the whole pattern works.

## 6. Documentation

- [x] 6.1 Note in this repo's CLAUDE.md: `bronze_neon` is populated by
      `neon_ecommerce_ingestion` (query-based Lakeflow Connect, `dev`-scoped only),
      seed data is Faker-generated synthetic, hard deletes in the source are not
      propagated (accepted limitation, not a bug), new source tables need a manual
      `table:` block + redeploy (schema-wide ingestion isn't used), and
      `verification/` exists as the standing way to re-check this pattern —
      distinct from `tests/`, which is pytest against `src/common/` only
