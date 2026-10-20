## Why

`pipeline-per-layer` lists ungm, iso, geonames and nsw_spatial as pending
refactor: each still has separate bronze ingestion and SCD pipelines, a
silver pipeline displayed `silver--landing--<source>`, and a verification
job not named by layer. They are the simplest sources to move: free APIs,
Landing only (no Silver Normalised), no Lakeflow Connect. acnc proved the
procedure (`acnc-two-pipelines`); this applies it to all four in one
change (user decision).

## What Changes

- **Bronze, per source: two pipelines become one.** The ingestion
  pipeline gains the SCD datasets (qualified names into
  `bronze_<source>_publish`, `pipelines.reset.allowed=false` on every SCD2
  table) and displays as `bronze--<source>--<target>`. The ten SCD tables
  move with the documented table move; the SCD pipelines are deleted, then
  leave the bundle.
- **One generic migration job** for the four sources (instead of acnc's
  one-off notebook): parameterised per source, idempotent, owner read from
  Unity Catalog, counts checked unchanged before the emptied pipeline is
  deleted. One task per source, run one after another; a failure stops
  only that source.
- **Silver**: Landing pipelines display as `silver--<source>--<target>`
  (display name only; nothing moves).
- **Verification**: jobs display as `verify--bronze--<source>--<target>`
  (keys unchanged). ungm's and nsw_spatial's SCD checks compare the SCD2
  current rows, not all versions, to raw (iso and geonames already do).
  The shared `verify_silver_landing` gains an optional `source` parameter
  so one source's Landing can be checked.
- **`run_<source>` jobs** for the four (bronze → verify bronze → silver →
  verify silver), auto-run by CI.
- Specs: the four sources leave the pending lists; their ingestion specs
  name the bronze pipeline and the verification display names.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `pipeline-per-layer`: ungm, iso, geonames, nsw_spatial removed from both
  pending lists.
- `ungm-unspsc-ingestion`, `iso-country-reference-ingestion`,
  `geonames-reference-ingestion`, `nsw-property-ingestion`: SCD tables
  built by the bronze pipeline; verification displayed by layer; ungm and
  nsw_spatial check SCD2 current rows.

## Model

Opus to propose (generalises acnc's migration to four sources, prd blast
radius); Sonnet to implement (repeats a proven procedure).

## Impact

- Per environment: four SCD pipelines removed, four ingestion pipelines
  changed, four Landing pipelines renamed, four verify jobs renamed, four
  `run_` jobs added, one temporary migration job added then removed.
- Ten tables re-homed per environment, none rebuilt.
- After the consolidation merges, CI runs four units in tst and prd, one
  after another (longer `main.yml` runs once).
- No schema, grant or iac change.
