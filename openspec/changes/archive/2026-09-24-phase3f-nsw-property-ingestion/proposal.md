## Why

Phase 3f adds a fifth source system and a second reusable custom Spark data
source connector, alongside 3d's CKAN connector (ACNC). The source is NSW's
"Land Parcel and Property Theme," served as an Esri ArcGIS REST
FeatureServer at `portal.spatial.nsw.gov.au` — confirmed live before this
proposal was written: ~4,225,857 rows, no auth required,
`returnGeometry=false` keeps the response to attributes only (no polygon
boundaries, which Spark/Delta isn't well-suited to store anyway). The SCD
key is `addressstringoid`, not `propid` as originally assumed — see
Cross-cutting discoveries below.

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
- `bronze_nsw_spatial.property_raw`: a Materialized View built on this
  connector, batch full-refresh (no incremental cursor is exposed by the
  layer)
- `nsw_property_row_limit` bundle variable: `dev`/`tst` → `500`; `prd` →
  `10000` — **not** unset/full, unlike every other source so far. This
  FeatureServer's own `maxRecordCount` (100) means a full ~4.2M-row pull
  needs ~42,259 requests; `10000` (100 requests) matches ACNC's `prd`
  request volume instead of scaling requests 630x. See Cross-cutting
  discoveries below.
- `property_scd1`/`property_scd2` in `bronze_nsw_spatial_publish` (Python
  only, matching every other source's scope decision), via
  `create_auto_cdc_from_snapshot_flow` directly against `property_raw`,
  keyed by `addressstringoid` (no quarantine pattern needed — confirmed
  zero `NULL`s and full uniqueness across a real 500-row `dev` run)
- A standing verification suite (`verify_nsw_property_pattern`), matching
  every other pattern's precedent

## Cross-cutting discoveries (mid-implementation, not planned upfront)

- **The SCD key is `addressstringoid`, not `propid`.** The first real
  `dev` run (500 rows, `row_limit=500`) showed only 486 distinct `propid`
  values. Investigated: this layer's actual grain is one row per address
  *within* a property, not one row per property — a unit block has one row
  per unit, all sharing the parent property's `propid`. `addressstringoid`
  is the field that's actually unique per row (confirmed: 500/500 distinct,
  zero `NULL`s). Fixed before building the SCD pipeline.
- **`page_size` bug**: the connector's default (1000) exceeded this
  FeatureServer's own `maxRecordCount` cap (100), which the server
  enforces silently (truncates rather than errors) — undercounting
  `partitions()`'s math and landing only 100 of the requested 500 rows on
  the first run. Fixed by reading `maxRecordCount` from the layer's own
  metadata and capping `page_size` to it.
- **`prd` scoped to `row_limit=10000`, not a full pull, discovered as a
  consequence of the `maxRecordCount` finding above.** Every other source
  in this project pulls the full dataset in `prd`; this one can't
  reasonably, since 100 rows/request × ~4.2M rows means ~42,259 requests —
  ~630x ACNC's `prd` request volume. Explicitly decided with the user:
  `10000` (100 requests) matches ACNC's `prd` request count instead.

## Capabilities

### New Capabilities
- `nsw-property-ingestion`: reusable ArcGIS FeatureServer custom data
  source connector, ingesting NSW's Land Parcel and Property Theme into
  `bronze_nsw_spatial`, with SCD1/SCD2 modeling into
  `bronze_nsw_spatial_publish`

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3f-nsw-property-schema` (proposed
alongside this change, not yet merged) — this change writes into
`bronze_nsw_spatial`/`bronze_nsw_spatial_publish`, which that change
creates. Should not deploy until that one has landed.

## Impact

- Adds new pipeline resource(s) and a verification job to the bundle
  across `dev`/`tst`/`prd`
- No changes to any existing source system's resources
