# ACNC Charity Register (via data.gov.au CKAN)

Australia's charity register, published as a public CKAN dataset. Free, no
auth. First consumer of this project's reusable CKAN connector.

- Base URL / portal: `data.gov.au`'s CKAN `datastore_search` REST API.
- Auth: none — public dataset.
- **A CKAN WAF blocks `requests`' default User-Agent with a 403** — confirmed
  via a real request before any code was written (same class of block UNGM's
  API applies). Fixed with an explicit `User-Agent` header.
- Code: `src/layers/bronze/acnc/charity_register_raw.py` (connector classes
  inline, not in `src/common/` — see below), `charity_register_quarantine.py`,
  `src/layers/bronze/acnc_publish/charity_register_valid.py` (private view),
  `charity_register_scd1.py`/`charity_register_scd2.py`.

## The reusable CKAN connector

`CkanDataSource`/`CkanDataSourceReader`, built on `pyspark.sql.datasource`
(the raw PySpark Custom Data Source API — not Lakeflow Connect's managed
catalog, not Databricks Labs' separate "Community Connectors" repo/CLI).
Generic over any CKAN portal's `datastore_search` REST API (data.gov.au,
data.gov.uk, etc.) — ACNC's Charity Register is the first real consumer, not
the only intended one.

- **Schema is inferred from CKAN's own field metadata**, not hardcoded to
  ACNC's fields — one `datastore_search?limit=1` call reads the resource's
  `fields` array and maps CKAN's `text`/`int`/`float`/`timestamp`/`bool` types
  to their Spark equivalents. This is what makes the connector reusable: a new
  CKAN dataset works by changing `resource_id`/`base_url`, no code change.
- **Reads are partitioned by offset range** (`DataSourceReader.partitions()`),
  not a single sequential pull — `page_size` rows per partition (default
  1000), honoring an optional `row_limit` option.
- **The connector's classes live inline in `charity_register_raw.py`, not in
  `src/common/`** — confirmed via a real `ModuleNotFoundError: No module named
  'common.ckan'`: custom Spark data source classes are cloudpickled for
  execution in a separate worker process that does not inherit the driver
  notebook's `sys.path` fix. A future second CKAN dataset would copy this
  file's connector block rather than import it.

## Ingestion in this project

`bronze_acnc.charity_register_raw` is a Materialized View built on
`spark.read.format("ckan")...load()`.

- **`acnc_row_limit` controls dev/tst blast radius**, not a separate test
  endpoint — ACNC/data.gov.au is a single public production dataset, no
  sandbox exists. `dev`/`tst` pull 500 rows; `prd` pulls the full dataset
  (~66k rows, confirmed via the CKAN API before this was built).
- **Quarantine pattern**: ~605 of ~66k charities (mostly Private Ancillary
  Funds) have a `NULL` ABN, confirmed via the CKAN SQL endpoint
  (`datastore_search_sql`) before SCD modeling was built — a real
  data-quality condition in the source, not a connector bug. Since `ABN` is
  the SCD key, these rows have no stable identity to track. Two datasets read
  the same `charity_register_raw` with complementary `@dp.expect_or_drop`
  conditions: `bronze_acnc.charity_register_quarantine` (public, `ABN IS
  NULL`) keeps them visible and queryable; a **private**
  (`private=True`) `charity_register_valid` view (`ABN IS NOT NULL`) feeds
  `charity_register_scd1`/`scd2`'s `create_auto_cdc_from_snapshot_flow`.
  Verification checks `raw = scd_count + quarantine_count`.

No platform-added `ingested_timestamp`/`transformed_timestamp` columns yet
(introduced later with AirROI — see NAMING.md's "Platform-added timestamp
columns" and `docs/registers/source_systems/airroi.md`). Apply if this source is
revisited.
