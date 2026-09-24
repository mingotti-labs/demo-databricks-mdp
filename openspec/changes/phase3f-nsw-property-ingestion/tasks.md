## 1. Bundle configuration

- [ ] 1.1 Add `nsw_property_service_url`, `nsw_property_layer_id`, and
      `nsw_property_row_limit` variables to `databricks.yml`:
      `nsw_property_row_limit` overridden per target — `dev`/`tst` →
      `"500"`, `prd` → `""` (unset, full dataset)

## 2. Reusable ArcGIS FeatureServer connector

- [ ] 2.1 Create the connector inline in `nsw_property_raw.py`:
      `ArcGisFeatureServerDataSource`/`...Reader` implementing `name()`,
      `schema()` (infers from the layer's `?f=json` metadata), `reader()`,
      `partitions()` (offset-range partitioning via
      `resultOffset`/`resultRecordCount`, honors `row_limit`),
      `read(partition)` (one `query` call per partition,
      `returnGeometry=false`)
- [ ] 2.2 Verify the connector's logic directly against the real NSW layer
      before wiring into a pipeline: confirm schema inference matches the
      known field list, confirm partitioning math against the live total
      feature count

## 3. Raw ingestion pipeline

- [ ] 3.1 Create `src/layers/bronze/nsw_spatial/property_raw.py` — a
      Materialized View built on the connector
- [ ] 3.2 Create `resources/pipelines/nsw_property_ingestion.pipeline.yml`
- [ ] 3.3 `databricks bundle validate` passes for dev
- [ ] 3.4 Deploy and run against `dev`; confirm `property_raw` row count
      matches `nsw_property_row_limit` (500) for `dev`

## 4. SCD modeling pipeline

- [ ] 4.1 Create `src/layers/bronze/nsw_spatial_publish/property_scd1.py`
      and `property_scd2.py` — `create_auto_cdc_from_snapshot_flow` against
      `bronze_nsw_spatial.property_raw` directly (no private filtering
      view needed, unlike ACNC — confirmed no NULL `propid` values), keyed
      by `propid`
- [ ] 4.2 Create `resources/pipelines/nsw_property_scd_modeling.pipeline.yml`
- [ ] 4.3 Deploy and run against `dev`; confirm `property_scd1`/
      `property_scd2` row counts match `property_raw`; check for duplicate
      `propid` values in the ingested data — if found, apply the
      established quarantine pattern (see design.md's Risks section)

## 5. Verification suite

- [ ] 5.1 Create `verification/verify_nsw_property_ingestion.py`
- [ ] 5.2 Create `verification/verify_nsw_property_scd.py`
- [ ] 5.3 Create `resources/jobs/verify_nsw_property_pattern.job.yml`
- [ ] 5.4 Run against `dev` — both tasks `SUCCESS`

## 6. Documentation

- [ ] 6.1 Add a "Sources" entry to CLAUDE.md for NSW property covering the
      connector design, provenance (Spatial Services / Property NSW
      Valnet), the `row_limit` blast-radius mechanism, and whether
      quarantine was needed in practice
- [ ] 6.2 Add `bronze/nsw_spatial/` and `bronze/nsw_spatial_publish/` to
      CLAUDE.md's repository-structure tree
