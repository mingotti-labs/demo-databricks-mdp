## 1. Neon Silver Landing

- [ ] 1.1 Create `src/layers/silver/landing/neon/` materialized views for
      `customers` and `products` (sourced from `customers_scd2` /
      `products_scd2`) and `orders` and `order_items` (sourced from
      `orders_scd1` / `order_items_scd1`), applying provenance columns, SCD
      column renames + `is_current` (customers/products only), and
      natural-key-leading column order per `silver.md`; verify the pipeline
      dataset graph shows all 4 tables
- [ ] 1.2 Add `resources/pipelines/silver_landing_neon.pipeline.yml`
      (`silver--landing--neon--${bundle.target}`, schema
      `silver_landing_neon`); verify `databricks bundle validate` passes

## 2. Clickstream Silver Landing

- [ ] 2.1 Create `src/layers/silver/landing/clickstream/` materialized view
      for `web_events` (sourced from `web_events_scd1`), applying provenance
      columns (`source_file_name` is null — confirmed `web_events_raw`
      doesn't capture `_metadata.file_path`, so there is nothing to
      propagate here despite this being a file-based source) and
      natural-key-leading column order; verify it appears in the pipeline
      dataset graph
- [ ] 2.2 Add `resources/pipelines/silver_landing_clickstream.pipeline.yml`
      (`silver--landing--clickstream--${bundle.target}`, schema
      `silver_landing_clickstream`); verify `databricks bundle validate`
      passes

## 3. UNGM Silver Landing

- [ ] 3.1 Create `src/layers/silver/landing/ungm/` materialized view for
      `unspsc_public` (sourced from `unspsc_public_scd2`), applying
      provenance columns, SCD column renames + `is_current`, and
      natural-key-leading column order
- [ ] 3.2 Add `resources/pipelines/silver_landing_ungm.pipeline.yml`
      (`silver--landing--ungm--${bundle.target}`, schema
      `silver_landing_ungm`); verify `databricks bundle validate` passes

## 4. ACNC Silver Landing

- [ ] 4.1 Create `src/layers/silver/landing/acnc/` materialized view for
      `charity_register` (sourced from `charity_register_scd2`), applying
      provenance columns, SCD column renames + `is_current`, and
      natural-key-leading column order
- [ ] 4.2 Add `resources/pipelines/silver_landing_acnc.pipeline.yml`
      (`silver--landing--acnc--${bundle.target}`, schema
      `silver_landing_acnc`); verify `databricks bundle validate` passes

## 5. NSW Spatial Silver Landing

- [ ] 5.1 Create `src/layers/silver/landing/nsw_spatial/` materialized view
      for `property` (sourced from `property_scd2`), applying provenance
      columns, SCD column renames + `is_current`, and natural-key-leading
      column order
- [ ] 5.2 Add `resources/pipelines/silver_landing_nsw_spatial.pipeline.yml`
      (`silver--landing--nsw_spatial--${bundle.target}`, schema
      `silver_landing_nsw_spatial`); verify `databricks bundle validate`
      passes

## 6. AirROI Silver Landing

- [ ] 6.1 Create `src/layers/silver/landing/airroi/` materialized views for
      `market_metrics_all` and `market_summary` (sourced from their
      respective `_scd2` objects), applying provenance columns, SCD column
      renames + `is_current`, and natural-key-leading column order
- [ ] 6.2 Add `resources/pipelines/silver_landing_airroi.pipeline.yml`
      (`silver--landing--airroi--${bundle.target}`, schema
      `silver_landing_airroi`); verify `databricks bundle validate` passes

## 7. Deploy and verify

- [ ] 7.1 Deploy all six pipelines to `dev` (`databricks bundle deploy -t
      dev`) and run each once; verify all six complete successfully
- [ ] 7.2 Add `verification/verify_silver_landing.py`, checking per entity:
      row-count parity against its selected Bronze Publish source object,
      non-null `source_name`/`transformed_timestamp` (`source_file_name` is
      null on all 10 today — no Bronze Publish object captures one yet;
      `ingested_timestamp` present and non-null only for AirROI's two
      entities, absent elsewhere), and — for the 7 SCD2-sourced entities —
      `is_current` correctly reflecting the active version; wire it into
      `resources/jobs/verify_silver_landing.job.yml`; verify the job run
      succeeds for all 10 entities
- [ ] 7.3 Confirm, for each of the 10 tables, that natural key(s) are the
      leading column(s) and no surrogate key column exists (via
      `databricks experimental aitools tools discover-schema`); verify
      against the entity table in design.md
