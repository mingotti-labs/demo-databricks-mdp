## Context

See proposal.md - Why. Roadmap Phase 3f, added during a spike into "does
data.gov.au have an all-of-Australia property dataset with
characteristics." Confirmed no single national dataset exists (property is
state/council jurisdiction in Australia, not federal); NSW's own ArcGIS
FeatureServer layer is the real, live, queryable source that came out of
that research. Full spike history lives in `demo-databricks-planning`'s
`poc/` folder.

**Provenance, confirmed via the layer's own CKAN metadata before this was
written**: published/custodied by **NSW Spatial Services** (DCS Spatial
Services, a business unit of the Department of Customer Service NSW), but
the underlying property attribute data originates one level further back —
**Property NSW's "Valnet" database** (their property/valuation system).
Spatial Services attaches that attribute data to cadastral geometry and
serves it via this FeatureServer. Updated daily, confirmed current
(`EPSG:7844` / GDA2020, not the older GDA94 service being retired).

## Goals / Non-Goals

**Goals:**
- A genuinely reusable ArcGIS FeatureServer connector — works against any
  Esri FeatureServer layer by `service_url`/`layer_id` config, not
  hardcoded to NSW's field list
- `property_raw` landing into `bronze_nsw_property`, modeled into
  SCD1/SCD2 in `bronze_nsw_property_publish`, same shape as every other
  source

**Non-Goals:**
- G-NAF / national address enrichment — explicitly deferred as optional
  roadmap Phase 3g, a separate, larger, later decision (see
  `demo-databricks-planning`'s `poc/gnaf-vs-gnaf-core-notes.md`)
- Parcel/property geometry (polygon boundaries) — `returnGeometry=false`
  throughout; Spark/Delta isn't geometry-native, and nothing in this
  project needs mapping/visualization yet
- SQL SCD1/SCD2 for this pattern — same scope decision every other custom
  connector source has made, for the same reason (the dual-language
  demonstration already exists via Neon)

## Decisions

**Connector classes defined inline in the pipeline file from the start —
not `src/common/`, and not rediscovered the hard way this time.**
ACNC's `phase3d-acnc-charity-register-ingestion` confirmed via a real
`ModuleNotFoundError` that custom Spark data source classes are
cloudpickled for execution in a separate worker process that doesn't
inherit the driver notebook's `sys.path` fix. Applying that finding
proactively: the ArcGIS connector's classes go directly in
`nsw_property_raw.py`, no `src/common/` import.

**`CREATE_MATERIALIZED_VIEW` already included in the CI/CD schema grant.**
Unlike ACNC (which discovered this gap reactively via a real pipeline
failure, `phase3d-cicd-materialized-view-grant`), this pattern's iac schema
proposal (`phase3f-nsw-property-schema`) includes the privilege from the
start — no reason to repeat that discovery a third time.

**Schema inferred from the FeatureServer's own `?f=json` layer metadata,
not hardcoded.**
Same principle as the CKAN connector's `schema()`: one metadata call reads
the layer's `fields` array (Esri field types: `esriFieldTypeInteger`,
`esriFieldTypeString`, `esriFieldTypeDate`, `esriFieldTypeDouble`, etc.)
and maps them to Spark equivalents. A new ArcGIS layer works by changing
`service_url`/`layer_id`, no code change.

**Partitioning by offset range, same shape as the CKAN connector.**
`resultOffset`/`resultRecordCount` is ArcGIS REST's equivalent of CKAN's
`offset`/`limit` — `partitions()` reads the layer's total feature count
(via `returnCountOnly=true`, capped by `row_limit`) and splits into
offset-range partitions.

**`returnGeometry=false` throughout.**
Confirmed during scoping: the layer's attribute fields alone (`propid`,
`address`, `propertytype`, `valnetpropertystatus`, `urbanity`, etc.) are
what's needed; polygon geometry would meaningfully increase response size
for no current use (no mapping/visualization requirement exists yet), and
Spark/Delta has no native geometry type — storing it would mean WKT
strings or a separate spatial library, out of scope here.

**No quarantine pattern needed — confirmed, not assumed.**
A real `WHERE propid IS NULL` count against the live layer returned `0`
before this proposal was written. Unlike ACNC's ABN, this key has no known
NULL-value population. Full uniqueness across all ~4.2M rows wasn't
exhaustively provable via the REST API's statistics endpoints cheaply
pre-build (a `returnDistinctValues`+`returnCountOnly` combination didn't
behave as expected); this will be confirmed the same way ACNC's actual
duplicate issue was caught — by querying the real ingested data after the
first run, not the source API in advance. If duplicates surface, the fix
is the same quarantine pattern ACNC established, applied here for the
first time on this source.

**`nsw_property_row_limit`, not a separate test layer, controls dev/tst
blast radius.**
Same reasoning as ACNC's `acnc_row_limit`: there's no sandbox version of
this FeatureServer to point lower environments at. `dev`/`tst` use a row
cap (proposed: `500`, matching ACNC's precedent — open to revision during
implementation); `prd` pulls the full ~4.2M rows.

## Risks / Trade-offs

- [`propid` uniqueness not exhaustively verified before implementation] →
  Mitigation: `NULL` count already confirmed at `0`; true duplicate
  detection happens via a real post-ingestion query during
  implementation's verification step, same methodology as every other
  source in this project. If duplicates exist, quarantine is the
  established, ready-to-apply fix.
- [~4.2M rows in `prd` is the largest single pull this project has
  attempted] → Mitigation: attributes-only (no geometry) keeps per-row
  size small; offset-range partitioning parallelizes the pull the same way
  ACNC's ~67-partition `prd` run already proved out at smaller scale.

## Migration Plan

Depends on `demo-databricks-iac`'s `phase3f-nsw-property-schema` landing
first (see proposal.md's cross-repo dependencies). Deploy to `dev`, verify
via `verify_nsw_property_pattern`, then promote to `tst`/`prd` the same way
prior patterns were. Rollback: remove the resources from the bundle; the
pattern only ever full-refreshes, no destructive state involved.
