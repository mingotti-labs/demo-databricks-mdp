## Why

`phase4a-silver-landing` gave the original six sources a source-aligned
Silver Landing foothold. ISO 3166
(`phase3i-iso-country-reference-ingestion`) and GeoNames
(`phase3j-geonames-reference-ingestion`) were onboarded to Bronze Publish
afterward and have no Silver Landing tables yet. This change closes that
gap using the exact same pattern — `silver-landing`'s capability spec is
already source-agnostic, so no requirement text changes.

## What Changes

- New `silver_landing_iso` schema with two Materialized Views:
  `country_codes` (from `bronze_iso_publish.country_codes_scd2`, keyed by
  `country_code_alpha2`) and `subdivision_codes` (from
  `bronze_iso_publish.subdivision_codes_scd2`, keyed by
  `subdivision_code`/`language_code`/`subdivision_name`).
- New `silver_landing_geonames` schema with four Materialized Views:
  `country_info` (from `country_info_scd2`, keyed by `iso_alpha2`),
  `admin1_codes`/`admin2_codes` (from their respective `_scd2` objects,
  keyed by `code`), and `cities` (from `cities_scd2`, keyed by
  `geonameid`).
- All six tables use the existing `src/common/silver_landing.py` `land()`
  helper — SCD column rename (`__START_AT`/`__END_AT` →
  `scd_valid_from_timestamp`/`scd_valid_to_timestamp`), `is_current`,
  provenance columns, natural-key-leading order — same as every other
  Silver Landing table. `ingested_timestamp` propagates unchanged from
  Bronze Publish for both sources (both stamp it, unlike the four
  non-AirROI sources from `phase4a-silver-landing`).
- Two new Lakeflow Declarative Pipelines
  (`silver--landing--{iso,geonames}--${bundle.target}`), one per source,
  matching the existing per-source Silver Landing pipeline grouping.
- Extend `verification/verify_silver_landing.py`'s `ENTITIES` list with
  the six new tables and the existing `verify_silver_landing` job; the
  `ingested_timestamp`-non-null check already special-cased for AirROI
  generalizes to any source whose Bronze Publish object carries one (now
  AirROI, ISO, and GeoNames).
- `docs/registers/data-sources.md`: iso/geonames entries updated from "not
  yet" to "yes" for Silver Landing consumption.

## Capabilities

### Modified Capabilities
(none — `silver-landing`'s existing requirements are already source-agnostic;
these six tables comply with them as written, no requirement text changes)

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s
`phase4b-silver-landing-iso-geonames-schemas` — this change's two new
pipelines write into `silver_landing_iso`/`silver_landing_geonames`, which
that change creates. Should not deploy until that one has landed.

## Impact

- Adds two new pipeline resources and six new Silver Landing tables to the
  bundle across `dev`/`tst`/`prd`
- Extends the existing `verify_silver_landing` job/notebook — no new
  verification job
- No changes to any existing source system's resources

## Model

Sonnet — repeats the established Silver Landing pattern from `phase4a-silver-landing`, using its own shared `land()` helper unchanged.
