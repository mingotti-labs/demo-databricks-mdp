## 1. Fetch helpers

- [x] 1.1 Created `src/common/geonames.py` with `fetch_geonames_dump(url,
      fieldnames)` (plain tab-delimited GET) and
      `fetch_geonames_zip_dump(url, inner_filename, fieldnames)` (zip GET +
      `zipfile`/`io.BytesIO` extraction) — `fieldnames` is explicit on both
      (revised during implementation): no GeoNames file gives
      `csv.DictReader` a usable header row on its own (three have none at
      all; `countryInfo.txt`'s real header is buried among `#`-prefixed
      documentation lines, not reliably first or last)
- [x] 1.2 Verified both helpers against all four real files directly
      (`curl`, then Python `requests`) before any pipeline code was written
      — confirmed row counts: 252 / 3,865 / 47,643 / 235,878

## 2. Raw ingestion pipeline

- [x] 2.1 Created `src/layers/bronze/geonames/country_info_raw.py` — a
      Materialized View calling `fetch_geonames_dump` against
      `countryInfo.txt`, table comment set to the CC BY 4.0 attribution
      text, `requests` declared as an explicit pipeline environment
      dependency, stamps `ingested_timestamp`
- [x] 2.2 Created `src/layers/bronze/geonames/admin1_codes_raw.py` against
      `admin1CodesASCII.txt`
- [x] 2.3 Created `src/layers/bronze/geonames/admin2_codes_raw.py` against
      `admin2Codes.txt`
- [x] 2.4 Created `src/layers/bronze/geonames/cities_raw.py` calling
      `fetch_geonames_zip_dump` against `cities500.zip`, applying GeoNames'
      documented 19-column geoname table schema
- [x] 2.4a Each of the four `_raw` datasets stamps a platform
      `ingested_timestamp` column (NAMING.md) — done from the start here,
      unlike ISO's change which added it as a correction
- [x] 2.5 Created `resources/pipelines/geonames_reference_ingestion.pipeline.yml`
- [x] 2.6 `databricks bundle validate` passed for dev/tst/prd
- [x] 2.7 Deployed and ran against `dev` (after
      `demo-databricks-iac`'s `phase3j-geonames-schema` landed) — confirmed
      row counts: 252 (`country_info_raw`), 3,865 (`admin1_codes_raw`),
      47,643 (`admin2_codes_raw`), 235,878 (`cities_raw`)

## 3. SCD modeling pipeline

- [x] 3.1 For each of the four keys (`iso_alpha2`, `code` x2, `geonameid`),
      verified uniqueness against the real fetched data (row count vs.
      distinct-key count) **before** wiring `create_auto_cdc_from_snapshot_flow`
      — all four held up (252/252, 3,865/3,865, 47,643/47,643,
      235,878/235,878), unlike ISO's `subdivision_code`. No deduplicating
      intermediate or quarantine table needed for any table
- [x] 3.2 No intermediate snapshot materialized view — each `<table>_scd2`
      reads a `@dp.temporary_view()` wrapping its `_raw` table directly,
      stamping `transformed_timestamp`
- [x] 3.3 **SCD2 only, no SCD1** (see design.md — same scope decision as
      ISO's, applied here from the start). Created `<table>_scd2.py` for
      all four tables via `create_auto_cdc_from_snapshot_flow`, keyed as
      verified in 3.1, excluding `ingested_timestamp`/`transformed_timestamp`
      via `track_history_except_column_list`
- [x] 3.4 Created `resources/pipelines/geonames_reference_scd_modeling.pipeline.yml`
- [x] 3.5 Deployed and ran against `dev` — each SCD2 table's current-row
      count (`__END_AT IS NULL`) matches its `_raw` counterpart exactly
      (252 / 3,865 / 47,643 / 235,878) — all four pre-verified keys held
      up in production, no surprises

## 4. Verification suite

- [x] 4.1 Created `verification/verify_geonames_reference_ingestion.py` —
      row counts, expected columns including `ingested_timestamp` (no
      quarantine check needed — see task 3.1)
- [x] 4.2 Created `verification/verify_geonames_reference_scd.py` — each
      SCD2 table's current-row count against its `_raw` row count (no
      quarantine invariant needed — see task 3.1)
- [x] 4.3 Created `resources/jobs/verify_geonames_reference_pattern.job.yml`
- [x] 4.4 Ran against `dev` — both tasks `SUCCESS`

## 5. Documentation

- [x] 5.1 Added a "Sources" entry to CLAUDE.md for GeoNames covering the
      pattern, the `cities500` scope decision, the CC BY 4.0 attribution
      mechanism, and the key-verification-before-wiring approach
- [x] 5.2 Added `bronze/geonames/` and `bronze/geonames_publish/` to
      CLAUDE.md's repository-structure tree
- [x] 5.3 Created `docs/registers/source_systems/geonames.md`, and added an
      entry to `docs/registers/data-sources.md`
