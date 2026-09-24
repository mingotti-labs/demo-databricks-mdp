## Why

Phase 3f adds a fifth source system and a second reusable custom Spark data
source connector, alongside 3d's CKAN connector (ACNC). The source is NSW's
"Land Parcel and Property Theme," served as an Esri ArcGIS REST
FeatureServer at `portal.spatial.nsw.gov.au` — confirmed live before this
proposal was written: ~4,225,857 properties, `propid` as a natural key with
zero `NULL` values, no auth required, `returnGeometry=false` keeps the
response to attributes only (no polygon boundaries, which Spark/Delta
isn't well-suited to store anyway).

This is deliberately scoped **without** the optional national address
enrichment (G-NAF) explored alongside it — see
`demo-databricks-planning`'s `poc/gnaf-vs-gnaf-core-notes.md` for that
research. The NSW property layer already has its own `address` field and
stands on its own; G-NAF is a separate, larger, explicitly-optional future
decision (roadmap Phase 3g), not a prerequisite for this change.

## What Changes

- A registerable Spark data source generic over any Esri ArcGIS REST
  FeatureServer layer (`service_url` + `layer_id` + optional `where`
  clause), defined inline in the pipeline file that registers it — applying
  the lesson from ACNC's `CkanDataSource` proactively this time (custom
  Spark data source classes are cloudpickled for execution in a separate
  worker process that doesn't inherit the driver notebook's `sys.path`,
  confirmed via a real failure during Phase 3d; not rediscovering that here):
  - `schema()` infers the Spark schema from the layer's own
    `?f=json` metadata endpoint (field names + Esri field types mapped to
    Spark types), not hardcoded to NSW's field list
  - `partitions()` reads the layer's total feature count (capped by an
    optional `row_limit` option) and splits into offset-range partitions of
    `page_size` features each (`resultOffset`/`resultRecordCount`), mirroring
    the CKAN connector's partitioning approach for a different REST shape
- `bronze_nsw_property.property_raw`: a Materialized View built on this
  connector, batch full-refresh (no incremental cursor is exposed by the
  layer)
- `nsw_property_row_limit` bundle variable: `dev`/`tst` → a small cap (TBD
  in design, likely `500`, matching the ACNC precedent), `prd` → unset
  (full ~4.2M rows)
- `property_scd1`/`property_scd2` in `bronze_nsw_property_publish` (Python
  only, matching every other source's scope decision), via
  `create_auto_cdc_from_snapshot_flow` directly against `property_raw`
  (no quarantine pattern needed here — confirmed zero `NULL propid` values
  via a real query before this proposal was written, unlike ACNC's
  NULL-ABN discovery)
- A standing verification suite (`verify_nsw_property_pattern`), matching
  every other pattern's precedent

## Capabilities

### New Capabilities
- `nsw-property-ingestion`: reusable ArcGIS FeatureServer custom data
  source connector, ingesting NSW's Land Parcel and Property Theme into
  `bronze_nsw_property`, with SCD1/SCD2 modeling into
  `bronze_nsw_property_publish`

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3f-nsw-property-schema` (proposed
alongside this change, not yet merged) — this change writes into
`bronze_nsw_property`/`bronze_nsw_property_publish`, which that change
creates. Should not deploy until that one has landed.

## Impact

- Adds new pipeline resource(s) and a verification job to the bundle
  across `dev`/`tst`/`prd`
- No changes to any existing source system's resources
