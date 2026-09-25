## Why

The city/locality half of the authoritative reference-data backbone
decided in `demo-databricks-planning`'s brainstorm
(`poc/reference-data-authoritative-sources-notes.md`) — no global ISO-style
standard exists at city granularity, so **GeoNames** (CC BY 4.0) is the
practical, comprehensive gazetteer sitting under ISO 3166's country/state
backbone (`phase3i-iso-country-reference-ingestion`).

## What Changes

- `src/common/geonames.py`: a small fetch helper —
  `fetch_geonames_dump(url)` for plain tab-delimited files (`countryInfo.txt`,
  `admin1CodesASCII.txt`, `admin2Codes.txt`) and
  `fetch_geonames_zip_dump(url, inner_filename)` for zip-wrapped files
  (`cities500.zip`) — both plain HTTPS GETs against
  `download.geonames.org/export/dump/`, confirmed via real fetches (no
  auth, no pagination, no WAF block).
- A Lakeflow Declarative Pipeline with four Materialized Views in
  `bronze_geonames`: `country_info_raw` (252 rows), `admin1_codes_raw`
  (3,865 rows, state/province-level), `admin2_codes_raw` (47,643 rows,
  county-level), and `cities_raw` (from `cities500.zip` — all populated
  places with population > 500, the smallest of GeoNames' official
  population-filtered variants) — all full-refresh batch pulls, each
  stamping a platform `ingested_timestamp` (NAMING.md).
- `<table>_scd2` (SCD2 only, no SCD1 — same scope decision made for
  `phase3i-iso-country-reference-ingestion`, applied here from the start)
  for all four tables in `bronze_geonames_publish`, Python only, via
  `create_auto_cdc_from_snapshot_flow` — same pattern as ISO's. Each flow
  stamps `transformed_timestamp` in an intermediate dataset immediately
  upstream of Auto CDC, excluding both timestamp columns via
  `track_history_except_column_list`.
- A standing verification suite (`verify_geonames_reference_pattern`).
- CC BY 4.0 attribution recorded as a Unity Catalog table comment on all
  four `_raw` tables.

## Capabilities

### New Capabilities
- `geonames-reference-ingestion`: GeoNames country/admin1/admin2/city
  gazetteer data into `bronze_geonames`, with SCD2 modeling into
  `bronze_geonames_publish`

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3j-geonames-schema` — this change
writes into `bronze_geonames`/`bronze_geonames_publish`, which that change
creates. Should not deploy until that one has landed (which itself depends
on `phase3i-iso-schema` landing first — see that change's proposal.md).

## Impact

- Adds new pipeline resource(s), a verification job, and
  `src/common/geonames.py` to the bundle across `dev`/`tst`/`prd`
- No changes to any existing source system's resources

## Model

Sonnet — same pattern as ISO's; switch to Opus if the zip-wrapped `cities500` pull or its size breaks the template.
