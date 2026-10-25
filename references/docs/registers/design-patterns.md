# Design Patterns Register

Every design pattern implemented in this repo, one entry each. Update it when a
pattern is introduced, split or retired. [data-sources.md](data-sources.md)
links each source to the patterns it uses.

**ID**: `<layer>_<technology>_<variant>_<language>`, language last and omitted
when the pattern is language-agnostic.
**Evidence**: where it was actually run — `prd`, `dev`, or `documented only`
(deployable reference material that was never run; its behaviour comes from
Databricks' docs, not from this repo).

**Finding a pattern from a table**: every table that uses a pattern carries the
Unity Catalog tag `design_pattern = <ID>`, set after each run by
`src/common/tag_design_patterns.py` (mapping: `src/common/design_patterns.yml`)
and, for the pattern-only tables, by the `tag--pattern` job in
`references/patterns/`. One value per table: the pattern that decides its shape.

## Ingestion (Bronze)

Entries marked `documented only` with no code come from Databricks' ingestion
overview (<https://docs.databricks.com/aws/en/ingestion/overview>, read
2026-10-21), which recommends starting with the most managed option and moving
down only if it does not fit. Release stages change; check the docs before
relying on one.

### bronze_lakeflow_query
Lakeflow Connect, query-based (gateway-free), reading a Postgres source through
a Unity Catalog Connection. Pick it for a relational source when CDC (which
needs classic compute) is unavailable. Hard deletes are not propagated; new
tables must be added explicitly. Code: `resources/pipelines/` (no source file).
Used by: [neon](data-sources.md#neon). Evidence: `dev`.

### bronze_lakeflow_saas
Lakeflow Connect managed connector pulling from a SaaS application (Salesforce,
Workday Reports, ServiceNow, Google Analytics 4, HubSpot, Confluence and others)
through a UC Connection, into governed Delta tables on a serverless ingestion
pipeline. Pick it for a SaaS source with a managed connector. Pipelines carry an
`ingestion_definition` (never `libraries`) and run triggered only; connector
availability varies by release stage, so check Databricks' connector reference.
Code: none. Used by: none (reference). Evidence: `documented only`.

### bronze_lakeflow_cdc
Lakeflow Connect database connector with change data capture: an ingestion
gateway in the customer's network stages change events to a UC Volume and a
serverless ingestion pipeline applies them as CDC. Pick it for a database that
exposes a change feed (SQL Server, PostgreSQL, MySQL, Oracle; release stage
varies by connector). The gateway
needs classic compute, which Free Edition does not have, which is why Neon uses
`bronze_lakeflow_query` instead.
Code: none. Used by: none (reference). Evidence: `documented only`.

### bronze_lakeflow_community
Community connectors: template-based connectors outside Databricks' managed
catalog (Databricks Labs' separate "Community Connectors" repo and CLI),
open source and not backed by Databricks SLAs. For a source with no managed
connector. Considered and not chosen for CKAN (see
`phase3d-acnc-charity-register-ingestion`'s design.md), which uses
`bronze_custom_ckan_python` instead.
Code: none. Used by: none (reference). Evidence: `documented only`.

### bronze_lakeflow_file
Lakeflow Connect file connectors: ingest files from services such as SharePoint
and Google Drive (managed connectors) into Delta tables. Pick it when files live
in an application, not on cloud object storage; for object storage use the
Auto Loader entries below. SFTP is listed among the standard connectors, where
you build the pipeline yourself.
Code: none. Used by: none (reference). Evidence: `documented only`.

### bronze_streaming_kafka_python
Continuous ingestion from a message bus (Apache Kafka, and per the docs also
Kinesis, Pub/Sub and Pulsar) with Structured Streaming, a Lakeflow pipeline or
Databricks SQL, at increasing levels of managed behaviour. Pick it when the
source is an event stream you can subscribe to. Distinct from Zerobus, where the
producer pushes.
Code: none. Used by: none (reference). Evidence: `documented only`.

### bronze_zerobus_direct_write
Zerobus Ingest: a push-based service where the producing application writes
records straight into a Unity Catalog Delta table over gRPC, REST or OTLP, with
no message bus. The table schema is the contract and is never auto-evolved;
records that no longer fit go to a fallback location. Pick it when you control
the producer. Release stage differs by feature (core managed and streaming
tables generally available; some options in preview or beta).
Code: none. Used by: none (reference). Evidence: `documented only`.

### bronze_federation_foreign_catalog
Lakehouse Federation: register the source as a foreign catalog and query it in
place, with no copy. Pick it for occasional or exploratory reads, not for
history or heavy workloads. The iac repo's Neon connectivity check used a
temporary foreign catalog this way (see `demo-databricks-iac`'s
`phase3a-neon-uc-connection`).
Code: none. Used by: none (reference). Evidence: `documented only`.

### bronze_delta_sharing
Receive a partner's data as a share, with no pipeline of your own. The docs'
ingestion overview lists this as OpenSharing. Pick it when the provider already
publishes a share.
Code: none. Used by: none (reference). Evidence: `documented only`.

### bronze_autoloader_add_new_columns_python
Auto Loader streaming table over files in a UC Volume, schema evolution mode
`addNewColumns`. A new column restarts the flow once and Databricks starts the
update again on its own. Pair with `rescuedDataColumn` as a safety net.
Code: `src/layers/bronze/clickstream/python_add_new_columns/`.
Used by: [clickstream](data-sources.md#clickstream). Evidence: `dev`.

### bronze_autoloader_{rescue,fail_on_new_columns,none}_python, bronze_autoloader_{add_new_columns,rescue,fail_on_new_columns,none}_sql
The other seven schema-evolution variants, each its own deployable pipeline with
an in-code write-up of its behaviour and recovery workflow.
Code: `references/patterns/src/bronze/autoloader_<mode>_<language>.{py,sql}` (a separate dev-only bundle).
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
Used by: [iso](data-sources.md#iso), [geonames](data-sources.md#geonames),
[wikipedia](data-sources.md#wikipedia) (an HTML table parsed by a helper).
Evidence: `prd`.

## Publish modelling (Bronze Publish)

### bronze_volume_csv_materialized_view_python
A CSV committed in the repo (`data/<source>/`), copied into a Unity Catalog
volume by the run job's first task, and read by a Materialized View with every
column as text. The repo is the master; the volume is overwritten on every run.
Code: `src/common/copy_repo_files.py`, `src/layers/bronze/portfolio/`.
Used by: [portfolio](data-sources.md#portfolio). Evidence: `dev`.

### bronze_publish_scd2_autocdc_snapshot_python
`create_auto_cdc_from_snapshot_flow` against a `_raw` source that is the full
current state per run (an upserted table or a Materialized View). Platform
timestamps are excluded from history tracking, but are still rewritten in place
on every current row each run (openspec `correct-platform-timestamps`), so it is
being replaced by `bronze_publish_scd2_autocdc_full_load_python` source by
source. Code: `src/layers/bronze/neon_publish/`.
Used by: neon. Evidence: `dev`.

### bronze_publish_scd2_autocdc_full_load_python
The bronze full pattern: `_raw` is a full load, so its `ingested_timestamp`
changes on every row at every load and is never part of the snapshot. Standard
`create_auto_cdc_from_snapshot_flow` from a temporary view that drops that
column; Auto CDC versions each snapshot with the pipeline update's time, written
as `__START_AT` on inserted versions and `__END_AT` on closed ones; unchanged
rows are not written; the SCD2 table has no platform timestamp columns. Change
data feed on, for Silver Landing. Not possible: streaming Auto CDC (a
materialized view cannot be streamed) and a function source carrying raw's
exact fetch time (it cannot read a dataset of its own pipeline). Code:
`src/layers/bronze/acnc_publish/charity_register_scd2.py`,
`src/layers/bronze/{ungm,iso,geonames,nsw_spatial,wikipedia,portfolio}_publish/`.
Used by: [acnc](data-sources.md#acnc), [ungm](data-sources.md#ungm),
[iso](data-sources.md#iso), [geonames](data-sources.md#geonames),
[nsw_spatial](data-sources.md#nsw_spatial), [wikipedia](data-sources.md#wikipedia),
[portfolio](data-sources.md#portfolio). Evidence: `prd` (acnc), `dev`.

### bronze_publish_scd1_autocdc_snapshot_python
The same snapshot flow, keeping only the latest version per key. Used where a
source also needs a "latest value" table. Reference only: code in the patterns
bundle, `references/patterns/src/bronze_publish/bronze_publish_scd1_autocdc_snapshot_python.py`
(table `pattern_bronze_publish.bronze_publish_scd1_autocdc_snapshot_python`).
Used by: neon `orders_scd1` and `order_items_scd1` (Landing's source) are the same flow in
`neon_publish/python/`. Evidence: `prd` (earlier use), `dev`.

### bronze_publish_scd1_autocdc_stream_python
Streaming `create_auto_cdc_flow`. Valid only against an append-only source:
against an upserted source it fails with `DELTA_SOURCE_TABLE_IGNORE_CHANGES`.
Code: `src/layers/bronze/clickstream_publish/python/`.
Used by: [clickstream](data-sources.md#clickstream). Evidence: `dev`.

### bronze_publish_scd1_autocdc_stream_sql
The same streaming pattern in SQL (`AUTO CDC INTO`), same append-only
restriction. Reference only: code in the patterns bundle,
`references/patterns/src/bronze_publish/bronze_publish_scd1_autocdc_stream_sql.sql`.
Evidence: `dev`.

### bronze_publish_scd1_materialized_view_sql
A plain passthrough Materialized View: an upserted `_raw` table already is the
latest value per key. Reference only: code in the patterns bundle,
`references/patterns/src/bronze_publish/bronze_publish_scd1_materialized_view_sql.sql`.
Evidence: `dev`.

### bronze_publish_scd2_merge_sql
A hand-rolled two-phase `MERGE` (expire the old version, insert the new one) run
as a job, because SQL has no snapshot Auto CDC and `MERGE` is invalid inside a
pipeline. Reference only: code in the patterns bundle,
`references/patterns/src/bronze_publish/bronze_publish_scd2_merge_sql.py` (job
`bronze--pattern--publish--scd2--merge--sql--<target>`). Evidence: `dev`.

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
Used by: no source since airroi moved to `silver_landing_change_feed_python`; candidate for the patterns bundle.

### silver_landing_change_feed_python
A streaming table that reads only the rows changed in its Bronze Publish SCD2
table (`readChangeFeed`) and applies them by version key with
`create_auto_cdc_flow`, so `transformed_timestamp` is stamped only on changed
rows, and sets `ingested_timestamp` to the version's `__START_AT`. Code:
`src/layers/silver/landing/{acnc,ungm,iso,geonames,nsw_spatial,airroi,wikipedia,portfolio}/`,
shared helper `land_changes` in `src/common/silver_landing.py`. Used by: acnc,
ungm, iso, geonames, nsw_spatial, airroi, wikipedia, portfolio. Evidence: `prd`
(acnc), `dev`.

### silver_normalised_spec_driven_python
Shared builders driven by a per-source YAML spec validated against a JSON
schema; extracted entities, bridges, quarantine and value lineage are generated,
not hand-written. Code: `src/layers/silver/normalised/`,
`src/common/normalised_spec.py`. Contract:
[normalised-spec](../normalised-spec/README.md).
Used by: [acnc](data-sources.md#acnc) (`prd`), [airroi](data-sources.md#airroi)
(`dev`). Tables are built by `silver_rebuild_keep_timestamps_python`; the
pipeline entry point was retired.

### silver_rebuild_keep_timestamps_python
A job task that rebuilds every table of a normalised spec in full and compares
each row with the previous table (every column but `transformed_timestamp`):
unchanged rows keep their stamp, new or changed rows get `current_timestamp()`,
rows that are gone are removed. Code: `src/common/keep_timestamps.py`,
`src/layers/silver/normalised/rebuild.py`. Used by:
[acnc](data-sources.md#acnc), [airroi](data-sources.md#airroi). Evidence: `dev`.

## Operations

### bronze_silver_pipeline_per_layer
One bronze pipeline and one silver pipeline per source, building the publish and
landing tables by qualified name, instead of one pipeline per pattern. Used by
acnc, ungm, iso, geonames, nsw_spatial, airroi, wikipedia, portfolio; clickstream
and neon follow it as
far as their sources allow. Evidence: `prd`.

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
