# Design Patterns Register

Every design pattern implemented in this repo, one entry each. Update it when a
pattern is introduced, split or retired. [data-sources.md](data-sources.md)
links each source to the patterns it uses.

**ID**: `<layer>_<technology>_<variant>_<language>`, language last and omitted
when the pattern is language-agnostic.
**Evidence**: where it was actually run — `prd`, `dev`, or `documented only`
(deployable reference material that was never run; its behaviour comes from
Databricks' docs, not from this repo).

## Ingestion (Bronze)

### bronze_lakeflow_query
Lakeflow Connect, query-based (gateway-free), reading a Postgres source through
a Unity Catalog Connection. Pick it for a relational source when CDC (which
needs classic compute) is unavailable. Hard deletes are not propagated; new
tables must be added explicitly. Code: `resources/pipelines/` (no source file).
Used by: [neon](data-sources.md#neon). Evidence: `dev`.

### bronze_autoloader_add_new_columns_python
Auto Loader streaming table over files in a UC Volume, schema evolution mode
`addNewColumns`. A new column restarts the flow once and Databricks starts the
update again on its own. Pair with `rescuedDataColumn` as a safety net.
Code: `src/layers/bronze/clickstream/python_add_new_columns/`.
Used by: [clickstream](data-sources.md#clickstream). Evidence: `dev`.

### bronze_autoloader_{rescue,fail_on_new_columns,none}_python, bronze_autoloader_{add_new_columns,rescue,fail_on_new_columns,none}_sql
The other seven schema-evolution variants, each its own deployable pipeline with
an in-code write-up of its behaviour and recovery workflow.
Code: the other `src/layers/bronze/clickstream/*/` folders.
Used by: none (reference). Evidence: `documented only`.

### bronze_custom_ckan_python
Reusable PySpark custom data source over any CKAN `datastore_search` API: schema
from CKAN field metadata, offset-range partitions, `row_limit` for non-prd
volume. The classes stay inline in the pipeline file because they are pickled to
a worker process that does not inherit `sys.path`.
Code: `src/layers/bronze/acnc/charity_register_raw.py`.
Used by: [acnc](data-sources.md#acnc). Evidence: `prd`.

### bronze_custom_arcgis_python
Reusable PySpark custom data source over an Esri ArcGIS REST FeatureServer
layer: schema from layer metadata, partitions by `resultOffset`, page size
capped to the server's own `maxRecordCount`.
Code: `src/layers/bronze/nsw_spatial/property_raw.py`.
Used by: [nsw_spatial](data-sources.md#nsw_spatial). Evidence: `prd`.

### bronze_rest_api_materialized_view_python
A Materialized View that re-fetches a REST API in full on each run through a
small source-scoped helper in `src/common/` (driver-side, `requests` with an
explicit User-Agent). Pick it when the source has no pagination or incremental
cursor. Code: `src/layers/bronze/ungm/`, `src/layers/bronze/airroi/`,
`src/common/ungm.py`, `src/common/airroi.py`.
Used by: [ungm](data-sources.md#ungm), [airroi](data-sources.md#airroi) (paid
API). Evidence: `prd`.

### bronze_file_materialized_view_python
A Materialized View over a static public CSV or text dump fetched by a helper in
`src/common/`, with a licence note as a table comment. Code:
`src/layers/bronze/iso/`, `src/layers/bronze/geonames/`,
`src/common/iso3166.py`, `src/common/geonames.py`.
Used by: [iso](data-sources.md#iso), [geonames](data-sources.md#geonames).
Evidence: `prd`.

## Publish modelling (Bronze Publish)

### bronze_publish_scd2_autocdc_snapshot_python
`create_auto_cdc_from_snapshot_flow` against a `_raw` source that is the full
current state per run (an upserted table or a Materialized View). Platform
timestamps are excluded from history tracking. Code:
`src/layers/bronze/{neon,ungm,acnc,nsw_spatial,airroi,iso,geonames}_publish/`.
Used by: neon, ungm, acnc, nsw_spatial, airroi, iso, geonames. Evidence: `prd`
(neon: `dev`).

### bronze_publish_scd1_autocdc_snapshot_python
The same snapshot flow, keeping only the latest version per key. Used where a
source also needs a "latest value" table. Code: `neon_publish/python/`,
`ungm_publish/`, `acnc_publish/`, `nsw_spatial_publish/`.
Used by: neon, ungm, acnc, nsw_spatial. Evidence: `prd` (neon: `dev`).

### bronze_publish_scd1_autocdc_stream_python
Streaming `create_auto_cdc_flow`. Valid only against an append-only source:
against an upserted source it fails with `DELTA_SOURCE_TABLE_IGNORE_CHANGES`.
Code: `src/layers/bronze/clickstream_publish/python/`.
Used by: [clickstream](data-sources.md#clickstream). Evidence: `dev`.

### bronze_publish_scd1_autocdc_stream_sql
The same streaming pattern in SQL (`AUTO CDC INTO`), same append-only
restriction. Code: `src/layers/bronze/clickstream_publish/sql/`.
Used by: [clickstream](data-sources.md#clickstream). Evidence: `dev`.

### bronze_publish_scd1_materialized_view_sql
A plain passthrough Materialized View: an upserted `_raw` table already is the
latest value per key. Code: `src/layers/bronze/neon_publish/sql/`.
Used by: [neon](data-sources.md#neon). Evidence: `dev`.

### bronze_publish_scd2_merge_sql
A hand-rolled two-phase `MERGE` (expire the old version, insert the new one) run
as a job, because SQL has no snapshot Auto CDC and `MERGE` is invalid inside a
pipeline. Code: `src/layers/bronze/neon_publish/scd2_merge/`.
Used by: [neon](data-sources.md#neon). Evidence: `dev`.

## Data quality

### bronze_quarantine_null_key_python
Two datasets read the same `_raw` table with complementary `expect_or_drop`
conditions: rows with a NULL SCD key go to a public `_quarantine` table, the rest
to a private view that feeds the SCD flow. Code:
`src/layers/bronze/acnc/charity_register_quarantine.py`,
`src/layers/bronze/acnc_publish/charity_register_valid.py`.
Used by: [acnc](data-sources.md#acnc). Evidence: `prd`.

### bronze_quarantine_duplicate_key_python
The same split, driven by a `row_number()` window over the SCD key: rank 1 feeds
the SCD flow, rank above 1 goes to quarantine. Code:
`src/layers/bronze/iso/subdivision_codes_quarantine.py`,
`src/layers/bronze/iso_publish/subdivision_codes_deduped.py`.
Used by: [iso](data-sources.md#iso). Evidence: `prd`.

## Silver

### silver_landing_materialized_view_python
One Materialized View per Bronze Publish table, applying the shared mechanical
conventions of Silver Landing. Code: `src/layers/silver/landing/`,
`src/common/silver_landing.py`. Contract: [silver.md](../medallion/silver.md).
Used by: all sources with a landing schema. Evidence: `prd` (neon, clickstream,
airroi: `dev`).

### silver_normalised_spec_driven_python
One shared pipeline driven by a per-source YAML spec validated against a JSON
schema; extracted entities, bridges, quarantine and value lineage are generated,
not hand-written. Code: `src/layers/silver/normalised/`,
`src/common/normalised_spec.py`. Contract:
[normalised-spec](../normalised-spec/README.md).
Used by: [acnc](data-sources.md#acnc) (`prd`), [airroi](data-sources.md#airroi)
(`dev`).

## Operations

### bronze_silver_pipeline_per_layer
One bronze pipeline and one silver pipeline per source, building the publish and
landing tables by qualified name, instead of one pipeline per pattern. Used by
acnc, ungm, iso, geonames, nsw_spatial; airroi, clickstream and neon are not yet
refactored. Evidence: `prd`.

### cicd_run_unit
A bundle job named `run_<unit>` chains everything a source produces; after a
`tst`/`prd` deploy CI runs only the units a change affects
(`cicd/affected_units.py`). Tag `ci_auto_run: "false"` keeps a unit out of CI.
Code: `resources/jobs/run_*.job.yml`, `cicd/affected_units.py`. Evidence: `prd`.

### ops_verification_job
A Databricks notebook that checks a deployed feature against real data
(connection liveness, row-count parity, referential integrity), chained into a
job per pattern. Code: `verification/`. Distinct from `tests/` (pytest) and from
`bundle validate`. Evidence: `dev` and `prd`.
