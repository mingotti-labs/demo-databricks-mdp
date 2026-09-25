# geonames-reference-ingestion Specification

## Purpose
Ingests GeoNames' country/admin1/admin2/city gazetteer data into
`bronze_geonames` via plain HTTPS dump-file downloads (no native connector,
no pagination), and models it as SCD2 in `bronze_geonames_publish` — the
city/locality half of the authoritative reference-data backbone decided in
`demo-databricks-planning`'s brainstorm.

## Requirements

### Requirement: Reusable GeoNames dump fetch helpers
`src/common/geonames.py` SHALL provide `fetch_geonames_dump(url)` for
plain tab-delimited dump files and `fetch_geonames_zip_dump(url,
inner_filename)` for zip-wrapped dump files, both performing a plain HTTP
GET with no authentication.

#### Scenario: Helpers work against all four real files
- **WHEN** `fetch_geonames_dump` is called against
  `http://download.geonames.org/export/dump/countryInfo.txt`,
  `admin1CodesASCII.txt`, and `admin2Codes.txt`, and
  `fetch_geonames_zip_dump` is called against `cities500.zip`
- **THEN** all four calls succeed and return the expected row shapes

### Requirement: Full-refresh batch ingestion into bronze_geonames
`country_info_raw`, `admin1_codes_raw`, `admin2_codes_raw`, and
`cities_raw` SHALL be Materialized Views that re-fetch their complete
source file on every run — none of these sources expose an incremental
cursor. All four SHALL stamp a platform `ingested_timestamp` column.

#### Scenario: Pipeline run lands data
- **WHEN** the pipeline is run against a target
- **THEN** `<catalog>.bronze_geonames.country_info_raw` has 252 rows,
  `admin1_codes_raw` has 3,865 rows, `admin2_codes_raw` has 47,643 rows,
  and `cities_raw` is populated with GeoNames' `cities500` dataset (all
  populated places with population > 500), all four with a populated
  `ingested_timestamp` column

### Requirement: SCD2 modeling, Python only, SCD2-only
`<table>_scd2` SHALL exist in `bronze_geonames_publish` for all four
tables, built via `create_auto_cdc_from_snapshot_flow` against each
`_raw` table (directly, or via a deduplicating private intermediate if the
key is found not to be unique — see the next requirement). No `_scd1`
variant SHALL be built for any table (a scope decision: low-change-frequency
reference data doesn't need a separate "latest value" table when SCD2's
`WHERE __END_AT IS NULL` gives the same thing). No SQL equivalent SHALL be
built for this pattern.

`country_info` SHALL be keyed by `iso_alpha2`; `admin1_codes` and
`admin2_codes` SHALL be keyed by `code`; `cities` SHALL be keyed by
`geonameid` — each confirmed unique against the real fetched data before
implementation relies on it (row count vs. distinct-key count); a key that
turns out not unique SHALL be corrected using the same evidence-first
approach ISO's `subdivision_code` finding used, not assumed correct from
the column name.

Each flow SHALL stamp a `transformed_timestamp` column in an intermediate
dataset immediately upstream of Auto CDC, and SHALL exclude both
`ingested_timestamp` and `transformed_timestamp` via
`track_history_except_column_list`.

#### Scenario: SCD2 tables match source row count on initial load
- **WHEN** the SCD pipeline is run after all four `_raw` tables are
  populated
- **THEN** each `<table>_scd2`'s current-row count (`__END_AT IS NULL`)
  matches its expected source count (its `_raw` counterpart's row count,
  or the distinct-key count if that table needed deduplication)

### Requirement: Duplicate-key quarantine (if a key collides)
If any of the four keys is found not to uniquely identify rows in the real
fetched data, a private deduplicating intermediate SHALL feed that table's
Auto CDC flow, and a public quarantine table in `bronze_geonames` SHALL
hold the complementary extra rows — same shape as ISO's
`subdivision_codes_deduped`/`subdivision_codes_quarantine`.

#### Scenario: Every raw row is accounted for, if quarantine applies
- **WHEN** a table needed deduplication
- **THEN** `raw_count == distinct_key_count + quarantine_count` for that
  table

### Requirement: License attribution on ingested tables
All four `_raw` tables SHALL carry a Unity Catalog table comment recording
the CC BY 4.0 attribution required by GeoNames.

#### Scenario: Attribution comment present
- **WHEN** any of the four `_raw` tables is inspected via `databricks
  tables get`
- **THEN** its `comment` field contains the required attribution text

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that all four
`_raw` tables are populated with their expected row counts and carry
`ingested_timestamp`, and that every table's `_scd2` current-row count
matches its expected source count — chained into one job
(`verify_geonames_reference_pattern`).

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_geonames_reference_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
