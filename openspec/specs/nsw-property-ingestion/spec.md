# nsw-property-ingestion Specification

## Purpose
Ingests NSW's Land Parcel and Property Theme (published by NSW Spatial
Services, sourced from Property NSW's Valnet database) into
`bronze_nsw_spatial` via a reusable custom Spark data source generic over
any Esri ArcGIS REST FeatureServer layer, and models it as SCD1/SCD2 in
`bronze_nsw_spatial_publish` — Phase 3f's second reusable connector class,
alongside 3d's CKAN connector.

## Requirements

### Requirement: Reusable ArcGIS FeatureServer data source connector
A registerable Spark data source (`spark.dataSource.register()`) SHALL
exist that is generic over any Esri ArcGIS REST FeatureServer layer —
schema inferred from the layer's own `?f=json` metadata, not hardcoded to
any one layer's fields. The connector's classes SHALL be defined inline in
the pipeline file that registers them, not in `src/common/` — the same
constraint confirmed for the CKAN connector applies equally here (custom
Spark data source classes are cloudpickled for execution in a separate
worker process that does not inherit the driver notebook's `sys.path`).

#### Scenario: Schema inference matches the source's real fields
- **WHEN** the connector's `schema()` is called against the NSW Land
  Parcel and Property Theme layer
- **THEN** the resulting `StructType` includes `propid`, `address`,
  `propertytype`, and the rest of the known field list, with types mapped
  from the layer's own Esri field type metadata

### Requirement: Partitioned reads without geometry
The connector's `DataSourceReader` SHALL split reads into offset-range
partitions (`resultOffset`/`resultRecordCount`), not a single sequential
pull, honoring an optional `row_limit` option that caps total rows read.
Geometry SHALL NOT be requested (`returnGeometry=false`) — only attribute
fields are ingested.

#### Scenario: Partition count reflects row_limit
- **WHEN** the connector is invoked with `row_limit=500` and the default
  `page_size`
- **THEN** exactly one partition is produced
- **WHEN** the connector is invoked with no `row_limit` against the full
  layer (~4.2M features) and the default `page_size`
- **THEN** more than one partition is produced, and the total rows read
  across all partitions equals the layer's total feature count

### Requirement: Row-limited in every environment, including prd
`property_raw` SHALL be pulled with `row_limit=500` when deployed to `dev`
or `tst`, and `row_limit=10000` when deployed to `prd` — not a full pull.
Unlike every other source in this project, `prd` does not pull the
complete dataset: this FeatureServer's own `maxRecordCount` (100) means a
full ~4.2M-row pull would need ~42,259 requests, confirmed too many for
routine use.

#### Scenario: Dev and tst are row-limited
- **WHEN** the pipeline is deployed and run against `dev` or `tst`
- **THEN** `property_raw` has exactly 500 rows

#### Scenario: Prd is row-limited too
- **WHEN** the pipeline is deployed and run against `prd`
- **THEN** `property_raw` has exactly 10000 rows, not the layer's full
  current feature count

### Requirement: Full-refresh batch ingestion into bronze_nsw_spatial
`property_raw` SHALL be a Materialized View that re-fetches the current
dataset (subject to `row_limit`) on every run — the source has no
incremental cursor, so full-refresh batch pull is the correct approach.

#### Scenario: Pipeline run lands data
- **WHEN** the pipeline is run against a target
- **THEN** `<catalog>.bronze_nsw_spatial.property_raw` exists and is
  populated

### Requirement: SCD1/SCD2 modeling, Python only
`property_scd1` and `property_scd2` SHALL exist in
`bronze_nsw_spatial_publish`, built via `create_auto_cdc_from_snapshot_flow`
against `property_raw` directly, keyed by `addressstringoid` — not `propid`,
which is shared across every address within the same property (a unit
block has one row per unit, all sharing one `propid`), confirmed via a real
run before this key was finalized. No SQL equivalent SHALL be built for
this pattern.

#### Scenario: SCD tables match source row count on initial load
- **WHEN** the SCD pipeline is run after `property_raw` is populated
- **THEN** `property_scd1` and `property_scd2` each have a row count
  matching `property_raw` exactly

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`property_raw` is populated and that `property_scd1`/`property_scd2` row
counts match it exactly, chained into one job
(`verify_nsw_property_pattern`) so the pattern can be re-checked on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_nsw_property_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
