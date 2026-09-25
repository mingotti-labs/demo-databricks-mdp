# NSW Spatial Services — Property layer

New South Wales' Land Parcel and Property Theme, published as an Esri ArcGIS
REST FeatureServer layer. Free, no auth. Second consumer of this project's
reusable ArcGIS FeatureServer connector, sourced ultimately from Property
NSW's Valnet database.

- Portal: `portal.spatial.nsw.gov.au`.
- Auth: none — public layer.
- A `curl`-style `User-Agent` header is set proactively, matching UNGM's and
  ACNC's confirmed WAF pattern — **not independently confirmed necessary for
  this specific server**, since every real request in this project used that
  header from the start. Safe no-op if actually unnecessary.
- Code: `src/layers/bronze/nsw_spatial/property_raw.py` (connector classes
  inline), `src/layers/bronze/nsw_spatial_publish/property_scd1.py`/
  `property_scd2.py`.

## The reusable ArcGIS FeatureServer connector

`ArcGisFeatureServerDataSource`/`ArcGisFeatureServerDataSourceReader`, generic
over any Esri ArcGIS REST FeatureServer layer, alongside ACNC's CKAN
connector.

- **Connector classes are inline in `property_raw.py`**, applying ACNC's
  `src/common/` lesson proactively — no `ModuleNotFoundError` rediscovery
  needed for this one.
- **Schema inferred from the layer's own `?f=json` metadata**, same principle
  as the CKAN connector's `schema()`.
- **Reads partitioned by offset range** (`resultOffset`/`resultRecordCount`,
  ArcGIS REST's equivalent of CKAN's `offset`/`limit`).
- **The connector must discover each FeatureServer's own `maxRecordCount`, not
  assume one** — confirmed via a real first run: this server caps
  `resultRecordCount` at 100, silently truncating a larger request instead of
  erroring, which undercounted the first `dev` run's row math (100 rows landed
  against a `row_limit` of 500). Fixed by reading `maxRecordCount` from the
  same metadata call `schema()` already makes and capping `page_size` to it.

## Ingestion in this project

`bronze_nsw_spatial.property_raw` is a Materialized View built on
`spark.read.format("arcgis_feature_server")...load()`.

- **The SCD key is `addressstringoid`, not `propid`** — caught via a real
  first run (486 distinct `propid` among 500 rows), not a pre-build check.
  This layer's actual grain is one row per *address* within a property, not
  one row per property: a unit block has one row per unit, all sharing the
  parent property's `propid`/`gurasid`/`principaladdresssiteoid`,
  differentiated only by `addressstringoid` (confirmed unique with zero
  `NULL`s across the real 500-row `dev` sample — not exhaustively checked at
  full ~4.2M-row scale). No quarantine pattern needed — this was a wrong key,
  not missing/dirty data.
- **`prd` does not pull the full dataset, unlike every other source in this
  project.** The `maxRecordCount` finding means a full ~4.2M-row pull would
  need ~42,259 requests (page_size capped at 100) — ~630x ACNC's `prd`
  request volume. `nsw_property_row_limit` caps `prd` at `10000` (100
  requests, matching ACNC's `prd` request count) instead of pulling
  everything; `dev`/`tst` use `500`.

No platform-added `ingested_timestamp`/`transformed_timestamp` columns yet
(introduced later with AirROI — see NAMING.md's "Platform-added timestamp
columns" and `docs/registers/source_systems/airroi.md`). Apply if this source is
revisited.

## Related, deferred

**G-NAF** (Geocoded National Address File) was researched as a possible
Phase 3g companion source but deferred as optional — see
`demo-databricks-planning/poc/gnaf-vs-gnaf-core-notes.md` for the full
findings.
