## Why

`demo-databricks-planning`'s brainstorm
(`poc/reference-data-authoritative-sources-notes.md`) decided a hybrid
authoritative reference-data backbone: ISO 3166-1/3166-2 for country/state,
GeoNames for city/locality (separate change, `phase3j-geonames-reference-ingestion`).
This change onboards the ISO half — the smallest, simplest ingestion
pattern in the project so far: two small CSV files, no auth, no
pagination, no WAF block.

## What Changes

- `src/common/iso3166.py`: a small fetch helper — `fetch_iso3166_csv(url)` —
  plain HTTPS GET against a raw GitHub CSV URL, parses the `#`-commented
  header and returns rows as dicts. Not a generic any-CSV framework; scoped
  to this source's two files.
- A Lakeflow Declarative Pipeline with two Materialized Views in
  `bronze_iso`: `country_codes_raw` (ISO 3166-1: alpha-2/alpha-3/numeric
  codes + short/long names, 249 rows) and `subdivision_codes_raw` (ISO
  3166-2: country code + subdivision code/name/category, 6,260 rows) — both
  full-refresh batch pulls, confirmed via real fetches against
  `raw.githubusercontent.com/ipregistry/iso3166` (CC BY-SA 4.0).
- `country_codes_scd1`/`country_codes_scd2` and
  `subdivision_codes_scd1`/`subdivision_codes_scd2` in `bronze_iso_publish`,
  Python only, via `create_auto_cdc_from_snapshot_flow` against each `_raw`
  table directly — same pattern as UNGM's, since both sources are "full
  current state per pull," not append-only.
- A standing verification suite (`verify_iso_reference_pattern`).
- CC BY-SA 4.0 attribution recorded as a Unity Catalog table comment on
  both `_raw` tables, not just in docs.

## Capabilities

### New Capabilities
- `iso-country-reference-ingestion`: ISO 3166-1/3166-2 country and
  subdivision reference data into `bronze_iso`, with SCD1/SCD2 modeling
  into `bronze_iso_publish`

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3i-iso-schema` — this change
writes into `bronze_iso`/`bronze_iso_publish`, which that change creates.
Should not deploy until that one has landed.

## Impact

- Adds new pipeline resource(s), a verification job, and
  `src/common/iso3166.py` to the bundle across `dev`/`tst`/`prd`
- No changes to any existing source system's resources
