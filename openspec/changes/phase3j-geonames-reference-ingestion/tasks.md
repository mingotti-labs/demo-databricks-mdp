## 1. Fetch helpers

- [ ] 1.1 Created `src/common/geonames.py` with `fetch_geonames_dump(url)`
      (plain tab-delimited GET) and `fetch_geonames_zip_dump(url,
      inner_filename)` (zip GET + `zipfile`/`io.BytesIO` extraction)
- [ ] 1.2 Verified both helpers against all four real files directly
      (`curl`, then Python `requests`) before any pipeline code was written

## 2. Raw ingestion pipeline

- [ ] 2.1 Created `src/layers/bronze/geonames/country_info_raw.py` — a
      Materialized View calling `fetch_geonames_dump` against
      `countryInfo.txt`, table comment set to the CC BY 4.0 attribution
      text, `requests` declared as an explicit pipeline environment
      dependency
- [ ] 2.2 Created `src/layers/bronze/geonames/admin1_codes_raw.py` against
      `admin1CodesASCII.txt`
- [ ] 2.3 Created `src/layers/bronze/geonames/admin2_codes_raw.py` against
      `admin2Codes.txt`
- [ ] 2.4 Created `src/layers/bronze/geonames/cities_raw.py` calling
      `fetch_geonames_zip_dump` against `cities500.zip`, applying GeoNames'
      documented 19-column geoname table schema
- [ ] 2.4a Each of the four `_raw` datasets stamps a platform
      `ingested_timestamp` column (NAMING.md) — done from the start here,
      unlike ISO's change which added it as a correction
- [ ] 2.5 Created `resources/pipelines/geonames_reference_ingestion.pipeline.yml`
- [ ] 2.6 `databricks bundle validate` passed for dev/tst/prd
- [ ] 2.7 Deployed and ran against `dev` — confirmed row counts: 252
      (`country_info_raw`), 3,865 (`admin1_codes_raw`), 47,643
      (`admin2_codes_raw`), and `cities_raw` populated

## 3. SCD modeling pipeline

- [ ] 3.1 For each of the four keys (`iso_alpha2`, `code` x2, `geonameid`),
      verify uniqueness against the real fetched data (row count vs.
      distinct-key count) **before** wiring `create_auto_cdc_from_snapshot_flow`
      — ISO's `subdivision_code` looked unique from the column name alone
      too, and wasn't (see `phase3i-iso-country-reference-ingestion`'s
      design.md). If any key collides, add a deduplicating private
      intermediate + a public quarantine table for the extras, same shape
      as `subdivision_codes_deduped.py`/`subdivision_codes_quarantine.py`
- [ ] 3.2 No intermediate snapshot materialized view — `source` reads
      directly from each `_raw` table (or the deduped intermediate from
      3.1, if needed) via a `@dp.temporary_view()`/private
      `@dp.materialized_view()` that stamps `transformed_timestamp`
- [ ] 3.3 **SCD2 only, no SCD1** (see design.md — same scope decision as
      ISO's, applied here from the start). Created `<table>_scd2.py` for
      all four tables via `create_auto_cdc_from_snapshot_flow`, keyed as
      verified in 3.1, excluding `ingested_timestamp`/`transformed_timestamp`
      via `track_history_except_column_list`
- [ ] 3.4 Created `resources/pipelines/geonames_reference_scd_modeling.pipeline.yml`
- [ ] 3.5 Deployed and ran against `dev`, spaced apart from other pipeline
      runs to avoid the known `RESOURCE_EXHAUSTED` serverless quota issue —
      each SCD2 table's current-row count (`__END_AT IS NULL`) matches its
      expected source count (its `_raw` counterpart's row count, or the
      distinct-key count if 3.1 found a collision)

## 4. Verification suite

- [ ] 4.1 Created `verification/verify_geonames_reference_ingestion.py` —
      row counts, expected columns including `ingested_timestamp`, and (if
      3.1 found a collision) quarantine non-empty
- [ ] 4.2 Created `verification/verify_geonames_reference_scd.py` — each
      SCD2 table's current-row count against its expected source count,
      plus `raw = distinct_key_count + quarantine_count` for any table
      that needed deduplication
- [ ] 4.3 Created `resources/jobs/verify_geonames_reference_pattern.job.yml`
- [ ] 4.4 Ran against `dev` — all tasks `SUCCESS`

## 5. Documentation

- [ ] 5.1 Added a "Sources" entry to CLAUDE.md for GeoNames covering the
      pattern, the `cities500` scope decision, and the CC BY 4.0
      attribution mechanism
- [ ] 5.2 Added `bronze/geonames/` and `bronze/geonames_publish/` to
      CLAUDE.md's repository-structure tree
- [ ] 5.3 Created `docs/registers/source_systems/geonames.md`, and added an
      entry to `docs/registers/data-sources.md`
