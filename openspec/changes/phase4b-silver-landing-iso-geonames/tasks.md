## 1. ISO Silver Landing

- [x] 1.1 Create `src/layers/silver/landing/iso/country_codes.py` — MV
      sourced from `bronze_iso_publish.country_codes_scd2`, keyed by
      `country_code_alpha2`, via `land()`
- [x] 1.2 Create `src/layers/silver/landing/iso/subdivision_codes.py` — MV
      sourced from `bronze_iso_publish.subdivision_codes_scd2`, keyed by
      `subdivision_code`/`language_code`/`subdivision_name`, via `land()`
- [x] 1.3 Add `resources/pipelines/silver_landing_iso.pipeline.yml`
      (`silver--landing--iso--${bundle.target}`, schema
      `silver_landing_iso`); `databricks bundle validate` passes

## 2. GeoNames Silver Landing

- [x] 2.1 Create `src/layers/silver/landing/geonames/country_info.py` — MV
      sourced from `country_info_scd2`, keyed by `iso_alpha2`, via `land()`
- [x] 2.2 Create `src/layers/silver/landing/geonames/admin1_codes.py` — MV
      sourced from `admin1_codes_scd2`, keyed by `code`, via `land()`
- [x] 2.3 Create `src/layers/silver/landing/geonames/admin2_codes.py` — MV
      sourced from `admin2_codes_scd2`, keyed by `code`, via `land()`
- [x] 2.4 Create `src/layers/silver/landing/geonames/cities.py` — MV
      sourced from `cities_scd2`, keyed by `geonameid`, via `land()`
- [x] 2.5 Add `resources/pipelines/silver_landing_geonames.pipeline.yml`
      (`silver--landing--geonames--${bundle.target}`, schema
      `silver_landing_geonames`); `databricks bundle validate` passes

## 3. Deploy and verify

- [x] 3.1 Deployed both pipelines to `dev` and ran each once — all 6 flows
      (`country_codes`/`subdivision_codes`, `country_info`/`admin1_codes`/
      `admin2_codes`/`cities`) `COMPLETED`
- [x] 3.2 Extended `verification/verify_silver_landing.py`'s `ENTITIES` list
      with all six new tables; generalized the `ingested_timestamp`
      non-null check to `SOURCES_WITH_INGESTED_TIMESTAMP = {"airroi",
      "iso", "geonames"}`
- [x] 3.3 Ran `verify_silver_landing` — `Silver Landing OK -- 16 entities
      verified` (10 existing + 6 new)
- [x] 3.4 Confirmed, for all 6 new tables, that natural key(s) lead and no
      surrogate key column exists (via `discover-schema`):
      `country_codes` → `country_code_alpha2`; `subdivision_codes` →
      `subdivision_code`, `language_code`, `subdivision_name`; `cities` →
      `geonameid` (spot-checked; `country_info`/`admin1_codes`/
      `admin2_codes` follow the same `land()` ordering)

## 4. Documentation

- [x] 4.1 Updated `docs/registers/data-sources.md`'s `iso`/`geonames`
      entries: "Consumed by Silver Landing" from "not yet" to "yes",
      naming the new tables
