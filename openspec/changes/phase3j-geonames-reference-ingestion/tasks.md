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
- [ ] 2.5 Created `resources/pipelines/geonames_reference_ingestion.pipeline.yml`
- [ ] 2.6 `databricks bundle validate` passed for dev/tst/prd
- [ ] 2.7 Deployed and ran against `dev` — confirmed row counts: 252
      (`country_info_raw`), 3,865 (`admin1_codes_raw`), 47,643
      (`admin2_codes_raw`), and `cities_raw` populated

## 3. SCD modeling pipeline

- [ ] 3.1 Created batch-snapshot views for all four `_raw` tables in
      `src/layers/bronze/geonames_publish/`
- [ ] 3.2 Created `<table>_scd1.py`/`<table>_scd2.py` for all four tables
      via `create_auto_cdc_from_snapshot_flow`, keyed as specced
      (`iso_alpha2`, `code`, `code`, `geonameid`)
- [ ] 3.3 Created `resources/pipelines/geonames_reference_scd_modeling.pipeline.yml`
- [ ] 3.4 Deployed and ran against `dev`, spaced apart from other pipeline
      runs to avoid the known `RESOURCE_EXHAUSTED` serverless quota issue —
      SCD table row counts match their `_raw` counterpart exactly

## 4. Verification suite

- [ ] 4.1 Created `verification/verify_geonames_reference_ingestion.py`
- [ ] 4.2 Created `verification/verify_geonames_reference_scd.py`
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
