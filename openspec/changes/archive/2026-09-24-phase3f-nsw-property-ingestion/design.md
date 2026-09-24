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
- `property_raw` landing into `bronze_nsw_spatial`, modeled into
  SCD1/SCD2 in `bronze_nsw_spatial_publish`, same shape as every other
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

**SCD key corrected to `addressstringoid`, not `propid` — discovered via a
real first run, not caught before implementation.**
The pre-implementation `NULL propid` check (0 nulls) was real but
insufficient: the first `dev` run (500 rows) showed only 486 distinct
`propid` values. Investigated before assuming a connector bug — grouping
by `propid` showed groups like 4 rows all sharing one `propid` and one
`gurasid`, but with 4 different `address` values (`"1A HUNTER AVENUE
CESSNOCK"`, `"1/1A HUNTER AVENUE CESSNOCK"`, `"2/1A ..."`, `"3/1A ..."`)
and 4 different `addressstringoid` values. This revealed the layer's real
grain: **one row per address instance within a property**, not one row
per property — a unit block has one row per unit, all sharing the parent
property's `propid`/`gurasid`/`principaladdresssiteoid`, differentiated
only by `addressstringoid`. `propid` was never a valid per-row key for
this layer; `addressstringoid` is — confirmed unique across all 500 rows
with zero `NULL`s in the same real query that caught the problem.
No quarantine pattern is needed: this isn't missing data to route around,
it's the correct key having been misidentified before a real run exposed
the layer's actual grain.
**`page_size` bug found and fixed in the same run**: the connector
defaulted `page_size` to 1000, but this FeatureServer's own
`maxRecordCount` caps `resultRecordCount` at 100 — silently truncating
each request instead of erroring, undercounting `partitions()`'s row math
(the first `dev` run landed only 100 rows against a `row_limit` of 500).
Fixed by reading `maxRecordCount` from the same layer metadata call
`schema()` already makes and using `min(requested_page_size,
maxRecordCount)` — the reusable connector now adapts to whatever cap a
given ArcGIS deployment enforces instead of assuming one.

**`nsw_property_row_limit`, not a separate test layer, controls dev/tst
blast radius — and, unlike every other source, `prd` is also capped.**
Same reasoning as ACNC's `acnc_row_limit` for `dev`/`tst` (`500`, no
sandbox version of this FeatureServer exists to point lower environments
at). `prd` is the real departure: this server's `maxRecordCount` (100,
discovered via the real first run, see above) means a full ~4.2M-row pull
needs ~42,259 requests — confirmed too many for routine use (time,
Free Edition serverless quota, and politeness to a public government
server all factor in). Explicitly decided with the user: `prd` caps at
`10000` (100 requests) instead of pulling everything, matching ACNC's own
`prd` request volume rather than scaling 630x past it.

## Risks / Trade-offs

- [The pre-implementation NULL check didn't catch the `propid` grain
  mismatch] → Confirmed as a real risk, not just theoretical: the first
  `dev` run caught it directly (486 distinct `propid` in 500 rows). Fixed
  by switching the SCD key to `addressstringoid`, verified unique with
  zero `NULL`s across the same real data. This project's own established
  lesson held again: pre-build API checks narrow risk, they don't replace
  verifying the real ingested data.
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
