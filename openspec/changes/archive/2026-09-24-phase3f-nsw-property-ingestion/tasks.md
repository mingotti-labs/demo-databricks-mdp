## 1. Bundle configuration

- [x] 1.1 Added `nsw_property_service_url`, `nsw_property_layer_id`, and
      `nsw_property_row_limit` variables to `databricks.yml`:
      `nsw_property_row_limit` overridden per target — `dev`/`tst` →
      `"500"`, `prd` → `"10000"` (not a full pull, unlike every other
      source -- see design.md's `maxRecordCount` finding: a full ~4.2M-row
      pull would need ~42,259 requests)

## 2. Reusable ArcGIS FeatureServer connector

- [x] 2.1 Created the connector inline in `property_raw.py`:
      `ArcGisFeatureServerDataSource`/`...Reader` implementing `name()`,
      `schema()` (infers from the layer's `?f=json` metadata), `reader()`,
      `partitions()` (offset-range partitioning via
      `resultOffset`/`resultRecordCount`, honors `row_limit`),
      `read(partition)` (one `query` call per partition,
      `returnGeometry=false`)
- [x] 2.2 Verified the connector's logic directly against the real NSW
      layer before wiring into a pipeline: schema inference matched the
      known field list (curl-style UA required, same WAF class as
      UNGM/ACNC), total feature count confirmed at 4,225,857

## 3. Raw ingestion pipeline

- [x] 3.1 Created `src/layers/bronze/nsw_spatial/property_raw.py` — a
      Materialized View built on the connector
- [x] 3.2 Created `resources/pipelines/nsw_property_ingestion.pipeline.yml`
- [x] 3.3 `databricks bundle validate` passed for dev
- [x] 3.4 First real run landed only 100 rows against `row_limit=500` --
      root cause: the connector's default `page_size` (1000) exceeded this
      FeatureServer's own `maxRecordCount` cap (100), which the server
      enforces silently (truncates, doesn't error), undercounting
      `partitions()`'s math. Fixed by reading `maxRecordCount` from the
      layer's own metadata and capping `page_size` to it. Second run:
      `property_raw` populated with exactly 500 rows

## 4. SCD modeling pipeline

- [x] 4.1 The planned SCD key (`propid`) was wrong -- the first real run
      showed only 486 distinct `propid` values among 500 rows. Investigated
      before assuming a bug: grouping by `propid` showed groups of rows
      sharing one `propid`/`gurasid`/`principaladdresssiteoid` but with
      different `address` and `addressstringoid` values -- the layer's real
      grain is one row per address *within* a property (a unit block has
      one row per unit). `addressstringoid` confirmed unique across all 500
      rows with zero `NULL`s -- the correct key
- [x] 4.2 Created `src/layers/bronze/nsw_spatial_publish/property_scd1.py`
      and `property_scd2.py` — `create_auto_cdc_from_snapshot_flow` against
      `bronze_nsw_spatial.property_raw` directly (no private filtering view
      needed -- no quarantine required), keyed by `addressstringoid`
- [x] 4.3 Created `resources/pipelines/nsw_property_scd_modeling.pipeline.yml`
- [x] 4.4 Deployed and ran against `dev` — `COMPLETED` on first attempt
      after the key fix; `property_scd1`/`property_scd2` row counts
      confirmed matching `property_raw` exactly (500/500/500)

## 5. Verification suite

- [x] 5.1 Created `verification/verify_nsw_property_ingestion.py`
- [x] 5.2 Created `verification/verify_nsw_property_scd.py` (also checks
      `addressstringoid` uniqueness directly, not just row-count parity)
- [x] 5.3 Created `resources/jobs/verify_nsw_property_pattern.job.yml`
- [x] 5.4 Ran against `dev` — both tasks `SUCCESS` (confirmed via real job
      run output: "property_raw ingestion OK -- 500 rows",
      "NSW property SCD1/SCD2 OK -- 500 rows each")

## 6. Documentation

- [x] 6.1 Added a "Sources" entry to CLAUDE.md for NSW Spatial Services
      covering the connector design, provenance (Spatial Services /
      Property NSW Valnet), the `row_limit` blast-radius mechanism
      (including `prd`'s 10000-row cap), the `maxRecordCount` discovery,
      and the `propid`-vs-`addressstringoid` grain correction
- [x] 6.2 Added `bronze/nsw_spatial/` and `bronze/nsw_spatial_publish/` to
      CLAUDE.md's repository-structure tree
