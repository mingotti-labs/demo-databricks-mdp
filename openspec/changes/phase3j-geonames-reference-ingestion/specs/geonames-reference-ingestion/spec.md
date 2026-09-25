# geonames-reference-ingestion Specification

## Purpose

Ingests GeoNames' country/admin1/admin2/city gazetteer data into
`bronze_geonames` via plain HTTPS dump-file downloads (no native connector,
no pagination), and models it as SCD1/SCD2 in `bronze_geonames_publish` —
the city/locality half of the authoritative reference-data backbone
decided in `demo-databricks-planning`'s brainstorm.

## ADDED Requirements

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
cursor.

#### Scenario: Pipeline run lands data
- **WHEN** the pipeline is run against a target
- **THEN** `<catalog>.bronze_geonames.country_info_raw` has 252 rows,
  `admin1_codes_raw` has 3,865 rows, `admin2_codes_raw` has 47,643 rows,
  and `cities_raw` is populated with GeoNames' `cities500` dataset (all
  populated places with population > 500)

### Requirement: SCD1/SCD2 modeling, Python only
`<table>_scd1`/`<table>_scd2` SHALL exist in `bronze_geonames_publish` for
all four tables, built via `create_auto_cdc_from_snapshot_flow` against a
batch snapshot of each `_raw` table. `country_info` SHALL be keyed by
`iso_alpha2`; `admin1_codes` and `admin2_codes` SHALL be keyed by `code`;
`cities` SHALL be keyed by `geonameid`. No SQL equivalent SHALL be built
for this pattern.

#### Scenario: SCD tables match source row count on initial load
- **WHEN** the SCD pipeline is run after all four `_raw` tables are
  populated
- **THEN** each `<table>_scd1`/`<table>_scd2` pair has a row count matching
  its `_raw` counterpart exactly

### Requirement: License attribution on ingested tables
All four `_raw` tables SHALL carry a Unity Catalog table comment recording
the CC BY 4.0 attribution required by GeoNames.

#### Scenario: Attribution comment present
- **WHEN** any of the four `_raw` tables is inspected via `databricks
  tables get`
- **THEN** its `comment` field contains the required attribution text

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that all four
`_raw` tables are populated with their expected row counts and that every
`_scd1`/`_scd2` pair matches its `_raw` counterpart's row count, chained
into one job (`verify_geonames_reference_pattern`).

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_geonames_reference_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
