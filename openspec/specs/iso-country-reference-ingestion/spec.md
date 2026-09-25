# iso-country-reference-ingestion Specification

## Purpose
Ingests ISO 3166-1 (country) and ISO 3166-2 (subdivision) reference data
into `bronze_iso` via a plain HTTPS CSV fetch (no native connector, no
pagination), and models it as SCD2 in `bronze_iso_publish` — the
country/state half of the authoritative reference-data backbone decided in
`demo-databricks-planning`'s brainstorm.

## Requirements

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
is the correct approach. Both SHALL stamp a platform `ingested_timestamp`
column.

#### Scenario: Pipeline run lands data
- **WHEN** the pipeline is run against a target
- **THEN** `<catalog>.bronze_iso.country_codes_raw` has 249 rows and
  `<catalog>.bronze_iso.subdivision_codes_raw` has 6,260 rows, both with a
  populated `ingested_timestamp` column

### Requirement: SCD2 modeling, Python only, SCD2-only
`country_codes_scd2` and `subdivision_codes_scd2` SHALL exist in
`bronze_iso_publish`, built via `create_auto_cdc_from_snapshot_flow`
against a batch snapshot of their respective source — not streaming Auto
CDC, since neither source is append-only. No SCD1 variant SHALL be built
for either table (a scope decision: low-change-frequency reference data
doesn't need a separate "latest value" table when SCD2's `WHERE __END_AT
IS NULL` gives the same thing). No SQL equivalent SHALL be built for this
pattern.

`country_codes_scd2` SHALL be keyed by `country_code_alpha2` alone.
`subdivision_codes_scd2` SHALL be keyed by `(subdivision_code,
language_code, subdivision_name)` — `subdivision_code` alone is not a
unique key (a subdivision can carry more than one localized name).

Both flows SHALL stamp a `transformed_timestamp` column in an intermediate
dataset immediately upstream of Auto CDC, and SHALL exclude both
`ingested_timestamp` and `transformed_timestamp` via
`track_history_except_column_list` so a rerun with no real source change
creates no spurious SCD2 history.

#### Scenario: SCD2 tables match source row count on initial load
- **WHEN** the SCD pipeline is run after both `_raw` tables are populated
- **THEN** `country_codes_scd2`'s current-row count (`__END_AT IS NULL`)
  equals `country_codes_raw`'s row count (249), and
  `subdivision_codes_scd2`'s current-row count equals the distinct-key
  count of `(subdivision_code, language_code, subdivision_name)` over
  `subdivision_codes_raw` (6,250 — not `subdivision_codes_raw`'s own row
  count of 6,260)

### Requirement: Subdivision duplicate-key quarantine
`subdivision_codes_raw` MAY contain more than one row for the same
`(subdivision_code, language_code, subdivision_name)` key (confirmed: 10 of
6,260 rows are genuine full-row duplicates in the source CSV). A private
`subdivision_codes_deduped` dataset SHALL dedupe on that key and feed
`subdivision_codes_scd2`'s Auto CDC flow. A public
`bronze_iso.subdivision_codes_quarantine` table SHALL hold the complementary
extra rows (rank > 1 per key), so every raw row is accounted for either in
the deduped count or in quarantine.

#### Scenario: Every raw row is accounted for
- **WHEN** `subdivision_codes_raw`'s row count, the distinct-key count over
  its SCD key, and `subdivision_codes_quarantine`'s row count are compared
- **THEN** `raw_count == distinct_key_count + quarantine_count`

### Requirement: License attribution on ingested tables
`country_codes_raw` and `subdivision_codes_raw` SHALL carry a Unity
Catalog table comment recording the CC BY-SA 4.0 attribution text required
by the source (ipregistry's ISO 3166 data republication).

#### Scenario: Attribution comment present
- **WHEN** `databricks tables get <catalog>.bronze_iso.country_codes_raw`
  (and the same for `subdivision_codes_raw`) is inspected
- **THEN** its `comment` field contains the required attribution text

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum): both `_raw`
tables are populated with their expected row counts and carry
`ingested_timestamp`; `subdivision_codes_quarantine` is non-empty and
`raw = distinct_key_count + quarantine_count`; both SCD2 tables' current-row
counts match their expected source count — chained into one job
(`verify_iso_reference_pattern`).

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_iso_reference_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
