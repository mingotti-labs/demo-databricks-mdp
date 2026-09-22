## 1. Bundle configuration

- [x] 1.1 Added `acnc_base_url`, `acnc_resource_id`, and `acnc_row_limit`
      variables to `databricks.yml`: `acnc_row_limit` overridden per
      target — `dev`/`tst` → `"500"`, `prd` → `""` (unset, full dataset)

## 2. Reusable CKAN connector

- [x] 2.1 Created `CkanDataSource`/`CkanDataSourceReader` implementing
      `name()`, `schema()` (infers from CKAN field metadata), `reader()`,
      `partitions()` (offset-range partitioning, honors `row_limit`),
      `read(partition)` (one `datastore_search` call per partition),
      explicit `User-Agent` header
- [x] 2.2 Verified the connector's logic directly against the real ACNC
      resource_id before wiring into a pipeline: confirmed schema (all
      `text` fields except `_id`), confirmed offset math for the last
      partition of a full pull (`offset=66000&limit=1000` → 363 records,
      total 66363, matching `range(0, 66363, 1000)`'s prediction exactly)
- [x] 2.3 First pipeline run failed with `ModuleNotFoundError: No module
      named 'common.ckan'` — the connector was originally in
      `src/common/ckan.py`, imported via the same `sys.path` fix
      `unspsc_public_raw.py` uses. Root cause: custom Spark data source
      classes are cloudpickled for execution in a separate worker process
      that doesn't inherit the driver's `sys.path` fix (confirmed against
      identical Databricks Community reports). Fixed by moving the
      connector classes inline into `charity_register_raw.py`; second run
      `COMPLETED`

## 3. Raw ingestion pipeline

- [x] 3.1 Created `src/layers/bronze/acnc/charity_register_raw.py` — a
      Materialized View built on `spark.read.format("ckan")...load()`
- [x] 3.2 Created `resources/pipelines/acnc_charity_register_ingestion.pipeline.yml`
- [x] 3.3 `databricks bundle validate` passed for dev (tst/prd share the
      same variable-driven config, not independently re-validated here)
- [x] 3.4 Deployed and ran against `dev`: `charity_register_raw` populated
      with exactly 500 rows (matching `acnc_row_limit`)

## 4. Quarantine (added mid-implementation, not originally planned)

- [x] 4.1 A `GROUP BY ABN HAVING COUNT(*) > 1` check on the freshly-loaded
      `dev` table found 11 rows sharing a `NULL` ABN (489 distinct ABNs
      among 500 rows); a `datastore_search_sql` count against the full
      dataset confirmed ~605 of ~66,363 dataset-wide
- [x] 4.2 Decided with the user: quarantine pattern, not a synthetic
      fallback key. Created `src/layers/bronze/acnc/charity_register_quarantine.py`
      (`@dp.expect_or_drop("has_no_abn", "ABN IS NULL")` against
      `charity_register_raw`)
- [x] 4.3 Deployed and ran — `charity_register_quarantine`: 11 rows,
      matching the earlier count exactly

## 5. SCD modeling pipeline

- [x] 5.1 Created `src/layers/bronze/acnc_publish/charity_register_valid.py`
      — a **private** MV (`@dp.expect_or_drop("has_abn", "ABN IS NOT
      NULL")` against `bronze_acnc.charity_register_raw`), the
      complementary filter to quarantine's
- [x] 5.2 Created `charity_register_scd1.py` and `charity_register_scd2.py`
      — `create_auto_cdc_from_snapshot_flow` against `charity_register_valid`
      (the private view, not `charity_register_raw` directly — unlike
      Neon/UNGM, ACNC's SCD source needs real filtering, not a passthrough)
      , keyed by `ABN`
- [x] 5.3 Created `resources/pipelines/acnc_charity_register_scd_modeling.pipeline.yml`
- [x] 5.4 Deployed and ran against `dev` — `COMPLETED` on first attempt;
      `charity_register_scd1`/`charity_register_scd2`: 489 rows each,
      confirming `raw(500) = scd(489) + quarantine(11)` exactly

## 6. Verification suite

- [x] 6.1 Created `verification/verify_acnc_charity_register_ingestion.py`
- [x] 6.2 Created `verification/verify_acnc_charity_register_scd.py`
      (checks `scd_count == raw_count - quarantine_count`, not raw-equals-
      SCD exactly)
- [x] 6.3 Created `resources/jobs/verify_acnc_charity_register.job.yml`
- [x] 6.4 Ran against `dev` — both tasks `SUCCESS`

## 7. Documentation

- [x] 7.1 Added a "Sources" entry to CLAUDE.md for ACNC covering the
      reusable connector design, the Community-Connectors-vs-direct-API
      decision, the inline-not-`src/common` discovery, the `row_limit`
      blast-radius mechanism, and the quarantine pattern
- [x] 7.2 Added `bronze/acnc/` and `bronze/acnc_publish/` to CLAUDE.md's
      repository-structure tree
- [x] 7.3 Added a `<table>_quarantine` naming note to NAMING.md
