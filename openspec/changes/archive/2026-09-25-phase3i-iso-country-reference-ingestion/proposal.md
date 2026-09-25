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
- A Lakeflow Declarative Pipeline with Materialized Views in `bronze_iso`:
  `country_codes_raw` (ISO 3166-1: alpha-2/alpha-3/numeric codes + short/
  long names, 249 rows) and `subdivision_codes_raw` (ISO 3166-2: country
  code + subdivision code/name/category, 6,260 rows) — both full-refresh
  batch pulls, confirmed via real fetches against
  `raw.githubusercontent.com/ipregistry/iso3166` (CC BY-SA 4.0). Both stamp
  a platform `ingested_timestamp` (NAMING.md).
- `country_codes_scd2` and `subdivision_codes_scd2` in `bronze_iso_publish`
  — **SCD2 only, no SCD1** (a scope decision made during implementation:
  low-change-frequency reference data doesn't need a separate "latest
  value" table when SCD2's `WHERE __END_AT IS NULL` gives the same thing;
  applies to this change and `phase3j-geonames-reference-ingestion`).
  Python only, via `create_auto_cdc_from_snapshot_flow`. Both stamp
  `transformed_timestamp` in an intermediate dataset just ahead of Auto
  CDC, excluding both timestamp columns via
  `track_history_except_column_list` — same pattern as AirROI's.
  - `country_codes_scd2` is keyed by `country_code_alpha2` (confirmed
    unique: 249 distinct of 249 rows).
  - `subdivision_codes_scd2` is keyed by `(subdivision_code, language_code,
    subdivision_name)`, **not `subdivision_code` alone** — corrected during
    implementation after a real pipeline run proved `subdivision_code`
    alone is not unique (6,260 rows, 5,046 distinct codes — a subdivision
    can carry more than one localized name) and that `language_code` alone
    still leaves 175 transliteration collisions. See design.md.
- Quarantine pattern for subdivisions: even the corrected 3-column key
  isn't quite enough — 10 of 6,260 rows are genuine full-row duplicates in
  the source CSV, which `create_auto_cdc_from_snapshot_flow` rejects
  outright (`DUPLICATE_KEY_VIOLATION`). `subdivision_codes_deduped`
  (private, feeds Auto CDC) and `subdivision_codes_quarantine` (public, in
  `bronze_iso`) read the same raw table with complementary
  `row_number()`-window logic, same shape as ACNC's quarantine pattern, so
  `raw = distinct_key_count + quarantine_count` exactly.
- A standing verification suite (`verify_iso_reference_pattern`), including
  the `raw = deduped + quarantine` invariant.
- CC BY-SA 4.0 attribution recorded as a Unity Catalog table comment on
  both `_raw` tables, not just in docs.

## Capabilities

### New Capabilities
- `iso-country-reference-ingestion`: ISO 3166-1/3166-2 country and
  subdivision reference data into `bronze_iso`, with SCD2 modeling into
  `bronze_iso_publish`

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3i-iso-schema` — this change
writes into `bronze_iso`/`bronze_iso_publish`, which that change creates.
Should not deploy until that one has landed.

## Impact

- Adds new pipeline resource(s), a verification job, and
  `src/common/iso3166.py` to the bundle across `dev`/`tst`/`prd`
- No changes to any existing source system's resources

## Model

Sonnet — repeats the established fetch helper, `_raw` MV, snapshot SCD1/SCD2, verification job pattern.
