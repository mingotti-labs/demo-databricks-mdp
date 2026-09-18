## 1. Pre-flight

- [ ] 1.1 Confirm `phase3a-neon-uc-connection` (iac) is applied and its live
      connectivity check passed — verify by re-running that change's own check
      (`SHOW SCHEMAS IN CONNECTION neon_dev` or equivalent) once more from here,
      rather than trusting it's still valid

## 2. Seed data

- [ ] 2.1 Create `src/seed_data/seed_neon_ecommerce.py`: Faker-seeded (fixed RNG
      seed for reproducibility), creates `customers`/`products`/`orders`/
      `order_items` (each with `updated_at`) if they don't exist, truncates and
      reseeds on every run, connects via the `neon-postgres` secret scope
- [ ] 2.2 Create `resources/jobs/seed_neon_ecommerce.job.yml`: serverless, notebook
      task pointing at 2.1, `environments:` block declaring `psycopg2-binary` and
      `faker` (not `%pip install`), no schedule — verify `databricks bundle
      validate --target dev`
- [ ] 2.3 Deploy and run the seed job — verify `databricks bundle run
      seed_neon_ecommerce --target dev` succeeds
- [ ] 2.4 Confirm data landed: query row counts for all four tables directly
      (e.g. via the `neon_dev` UC Connection or a quick psycopg2 check) — verify
      counts are non-zero and match what the notebook was configured to generate

## 3. Ingestion pipeline

- [ ] 3.1 Create `resources/pipelines/neon_ecommerce_ingestion.pipeline.yml`:
      `ingestion_definition.connection_name = neon_dev`, one `table` object per
      source table (`source_catalog: app`, `source_schema: public`,
      `table_configuration.query_based_connector_config.cursor_columns:
      [updated_at]`, `destination_catalog: ${var.catalog}`,
      `destination_schema: bronze_neon`) — verify `databricks bundle validate
      --target dev`
- [ ] 3.2 Deploy — verify `databricks bundle deploy --target dev` creates the
      pipeline with no errors
- [ ] 3.3 Run — verify `databricks bundle run neon_ecommerce_ingestion --target
      dev` succeeds
- [ ] 3.4 Confirm landed data: query `mdp_dev.bronze_neon.{customers,products,
      orders,order_items}` — verify row counts match the seed data (task 2.4)

## 4. Manual walkthrough guide

- [ ] 4.1 Write `docs/lakeflow-connect-manual-guide.md`: mirrors the UI-driven
      equivalent of tasks 3.1-3.3 (Catalog Explorer > Connections, then the
      ingestion pipeline creation wizard) — verify it's accurate by comparing
      against what was actually clicked/configured, not written from memory of how
      the UI is expected to look

## 5. Verification suite

- [ ] 5.1 Create `verification/verify_neon_connection.py`: asserts `SHOW SCHEMAS IN
      CONNECTION neon_dev` returns `public` — fails loudly (plain `assert`) if not
- [ ] 5.2 Create `verification/verify_seed_data.py`: asserts all four Neon tables
      have rows, and referential integrity holds (every `orders.customer_id` exists
      in `customers`, every `order_items.order_id`/`product_id` exists in
      `orders`/`products`)
- [ ] 5.3 Create `verification/verify_bronze_neon_ingestion.py`: asserts
      `mdp_dev.bronze_neon.*` row counts match the Neon source counts for all four
      tables
- [ ] 5.4 Create `resources/jobs/verify_neon_ecommerce_pattern.job.yml`: three
      tasks (5.1-5.3) chained via `depends_on` in that order — verify `databricks
      bundle validate --target dev`
- [ ] 5.5 Deploy and run — verify `databricks bundle run
      verify_neon_ecommerce_pattern --target dev` succeeds end-to-end; this run
      *is* the final proof the whole pattern works, not a separate afterthought

## 6. Documentation

- [ ] 6.1 Note in this repo's CLAUDE.md: `bronze_neon` is populated by
      `neon_ecommerce_ingestion` (query-based Lakeflow Connect, `dev`-scoped only),
      seed data is Faker-generated synthetic, hard deletes in the source are not
      propagated (accepted limitation, not a bug), new source tables need a manual
      `table:` block + redeploy (schema-wide ingestion isn't used), and
      `verification/` exists as the standing way to re-check this pattern —
      distinct from `tests/`, which is pytest against `src/common/` only
