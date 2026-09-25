# iso-country-reference-ingestion Specification

## Purpose

Ingests ISO 3166-1 (country) and ISO 3166-2 (subdivision) reference data
into `bronze_iso` via a plain HTTPS CSV fetch (no native connector, no
pagination), and models it as SCD1/SCD2 in `bronze_iso_publish` — the
country/state half of the authoritative reference-data backbone decided in
`demo-databricks-planning`'s brainstorm.

## ADDED Requirements

### Requirement: Reusable ISO 3166 CSV fetch helper
`src/common/iso3166.py` SHALL provide a function that performs an HTTP GET
against a given raw CSV URL and returns parsed rows, skipping `#`-prefixed
comment header lines.

#### Scenario: Helper works against both real files
- **WHEN** the helper is called against
  `https://raw.githubusercontent.com/ipregistry/iso3166/master/countries.csv`
  and separately against `.../subdivisions.csv`
- **THEN** both calls succeed and return the expected row shapes (country:
  alpha-2/alpha-3/numeric codes + short/long names; subdivision: country
  code, subdivision code, subdivision name, category)

### Requirement: Full-refresh batch ingestion into bronze_iso
`country_codes_raw` and `subdivision_codes_raw` SHALL be Materialized
Views that re-fetch their complete source file on every run — neither
source has pagination or an incremental cursor, so full-refresh batch pull
is the correct approach.

#### Scenario: Pipeline run lands data
- **WHEN** the pipeline is run against a target
- **THEN** `<catalog>.bronze_iso.country_codes_raw` has 249 rows and
  `<catalog>.bronze_iso.subdivision_codes_raw` has 6,260 rows

### Requirement: SCD1/SCD2 modeling, Python only
`country_codes_scd1`/`country_codes_scd2` and
`subdivision_codes_scd1`/`subdivision_codes_scd2` SHALL exist in
`bronze_iso_publish`, built via `create_auto_cdc_from_snapshot_flow`
against a batch snapshot of their respective `_raw` table — not streaming
Auto CDC, since neither source is append-only. `country_codes` SHALL be
keyed by `country_code_alpha2`; `subdivision_codes` SHALL be keyed by
`subdivision_code`. No SQL equivalent SHALL be built for this pattern.

#### Scenario: SCD tables match source row count on initial load
- **WHEN** the SCD pipeline is run after both `_raw` tables are populated
- **THEN** `country_codes_scd1`/`country_codes_scd2` each have 249 rows and
  `subdivision_codes_scd1`/`subdivision_codes_scd2` each have 6,260 rows

### Requirement: License attribution on ingested tables
`country_codes_raw` and `subdivision_codes_raw` SHALL carry a Unity
Catalog table comment recording the CC BY-SA 4.0 attribution text required
by the source (ipregistry's ISO 3166 data republication).

#### Scenario: Attribution comment present
- **WHEN** `databricks tables get <catalog>.bronze_iso.country_codes_raw`
  (and the same for `subdivision_codes_raw`) is inspected
- **THEN** its `comment` field contains the required attribution text

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that both `_raw`
tables are populated with their expected row counts and that both pairs of
SCD tables match their `_raw` counterpart's row count, chained into one
job (`verify_iso_reference_pattern`).

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_iso_reference_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
