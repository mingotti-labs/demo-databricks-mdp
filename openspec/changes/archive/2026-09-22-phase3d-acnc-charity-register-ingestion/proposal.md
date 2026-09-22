## Why

Phase 3d formalizes the "custom Python/API ingestion" pattern 3c proved out
(UNGM) into a genuinely **reusable connector**, built on the PySpark Custom
Data Source API (`pyspark.sql.datasource.DataSource`/`DataSourceReader`) —
not a one-off fetch helper. The concrete source is the ACNC (Australian
Charities and Not-for-profits Commission) Charity Register, published on
data.gov.au's public CKAN Data API. Unlike UNGM's bespoke `fetch_ungm_endpoint`
helper, this connector is generic over CKAN's `datastore_search` API shape
(any CKAN-hosted dataset from any government portal, parameterized by
`base_url`/`resource_id`), with ACNC as the first real consumer.

This is deliberately **not** Lakeflow Connect (Databricks' managed connector
catalog — Salesforce, ServiceNow, SQL Server CDC, etc., which ships
pre-built connectors only) and **not** the separate Databricks Labs
"Community Connectors" framework (external repo/CLI tooling, unverified
Free Edition support). It is the underlying SDK both of those are built on,
used directly, deployed the same way every other pipeline in this repo is
(DAB bundle, no external tooling).

## What Changes

- `CkanDataSource`/`CkanDataSourceReader` — a registerable Spark data
  source (`spark.dataSource.register()`) generic over any CKAN portal's
  `datastore_search` REST API, defined inline in
  `charity_register_raw.py` (not `src/common/` — see Cross-cutting
  discoveries below for why):
  - `schema()` infers the Spark schema from CKAN's own field metadata (one
    lightweight `datastore_search?limit=1` call), mapping CKAN's `text`/
    `int`/`float`/`timestamp`/`bool` types to `StringType`/`LongType`/
    `DoubleType`/`TimestampType`/`BooleanType` — no hardcoded ACNC field list
  - `partitions()` reads `result.total` (capped by an optional `row_limit`
    option) and splits it into offset-range partitions of `page_size` rows
    each, so `read(partition)` fetches one page per partition — genuine
    parallel reads, not a single sequential pull
  - Same browser-like `User-Agent` header fix `ungm.py` needed — data.gov.au
    runs the same class of WAF that blocks `requests`' default UA (confirmed
    via a real request before any code was written)
- `bronze_acnc.charity_register_raw`: a Materialized View built on
  `spark.read.format("ckan").option(...).load()`, batch full-refresh (the
  ACNC dataset is a weekly full snapshot, no incremental cursor)
- `acnc_row_limit` bundle variable: `dev`/`tst` → `500` (row-limited, since
  ACNC has no separate sandbox dataset to point lower environments at
  the way UNGM's test endpoint did), `prd` → unset (full ~66k rows)
- `bronze_acnc.charity_register_quarantine`: rows with a `NULL` ABN
  (~605 of ~66k, discovered mid-implementation — see below), kept visible
  rather than silently dropped
- A private `charity_register_valid` view (ABN-not-null) in the SCD
  modeling pipeline, feeding `charity_register_scd1`/`charity_register_scd2`
  in `bronze_acnc_publish` (Python only, matching UNGM's scope decision)
  via `create_auto_cdc_from_snapshot_flow`, keyed by `ABN`
- A standing verification suite (`verify_acnc_charity_register`), matching
  every other pattern's precedent, checking `raw = scd_count +
  quarantine_count`

## Cross-cutting discoveries (mid-implementation, not planned upfront)

- **The connector can't live in `src/common/` as originally designed.**
  A real `ModuleNotFoundError: No module named 'common.ckan'` on the first
  run proved that custom Spark data source classes are cloudpickled for
  execution in a separate worker process that doesn't inherit the driver
  notebook's `sys.path` fix (the mechanism `unspsc_public_raw.py` relies
  on for its own, purely driver-side import). Fixed by defining the
  connector classes inline in `charity_register_raw.py` instead — matches
  reports of the identical failure in the Databricks Community.
- **~605 of ~66,363 charities have a `NULL` ABN** (confirmed via the CKAN
  SQL endpoint, `datastore_search_sql`), mostly Private Ancillary Funds —
  a real source data-quality condition, not a connector bug. Since `ABN`
  is the SCD key, these rows have no stable identity. Addressed with a
  quarantine pattern (see What Changes) rather than silently dropping them
  or picking an unsafe fallback key.

## Capabilities

### New Capabilities
- `acnc-charity-register-ingestion`: reusable CKAN custom data source
  connector, ingesting the ACNC Charity Register into `bronze_acnc`, with
  a quarantine table for un-trackable rows and SCD1/SCD2 modeling into
  `bronze_acnc_publish`

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3d-acnc-schema` (merged) — this
change writes into `bronze_acnc`/`bronze_acnc_publish`, which that change
created.

## Impact

- Adds new pipeline resource(s) and a verification job to the bundle
  across `dev`/`tst`/`prd`
- No changes to any existing source system's resources
