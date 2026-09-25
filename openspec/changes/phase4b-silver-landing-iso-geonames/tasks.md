## 1. ISO Silver Landing

- [ ] 1.1 Create `src/layers/silver/landing/iso/country_codes.py` — MV
      sourced from `bronze_iso_publish.country_codes_scd2`, keyed by
      `country_code_alpha2`, via `land()`
- [ ] 1.2 Create `src/layers/silver/landing/iso/subdivision_codes.py` — MV
      sourced from `bronze_iso_publish.subdivision_codes_scd2`, keyed by
      `subdivision_code`/`language_code`/`subdivision_name`, via `land()`
- [ ] 1.3 Add `resources/pipelines/silver_landing_iso.pipeline.yml`
      (`silver--landing--iso--${bundle.target}`, schema
      `silver_landing_iso`); verify `databricks bundle validate` passes

## 2. GeoNames Silver Landing

- [ ] 2.1 Create `src/layers/silver/landing/geonames/country_info.py` — MV
      sourced from `country_info_scd2`, keyed by `iso_alpha2`, via `land()`
- [ ] 2.2 Create `src/layers/silver/landing/geonames/admin1_codes.py` — MV
      sourced from `admin1_codes_scd2`, keyed by `code`, via `land()`
- [ ] 2.3 Create `src/layers/silver/landing/geonames/admin2_codes.py` — MV
      sourced from `admin2_codes_scd2`, keyed by `code`, via `land()`
- [ ] 2.4 Create `src/layers/silver/landing/geonames/cities.py` — MV
      sourced from `cities_scd2`, keyed by `geonameid`, via `land()`
- [ ] 2.5 Add `resources/pipelines/silver_landing_geonames.pipeline.yml`
      (`silver--landing--geonames--${bundle.target}`, schema
      `silver_landing_geonames`); verify `databricks bundle validate`
      passes

## 3. Deploy and verify

- [ ] 3.1 Deploy both pipelines to `dev` and run each once; verify both
      complete successfully
- [ ] 3.2 Extend `verification/verify_silver_landing.py`'s `ENTITIES` list
      with all six new tables; generalize the `ingested_timestamp` non-null
      check from `entity["source"] == "airroi"` to
      `entity["source"] in ("airroi", "iso", "geonames")`
- [ ] 3.3 Run `verify_silver_landing` — verify it succeeds for all 16
      entities (10 existing + 6 new)
- [ ] 3.4 Confirm, for each of the 6 new tables, that natural key(s) are
      the leading column(s) and no surrogate key column exists (via
      `databricks experimental aitools tools discover-schema`)

## 4. Documentation

- [ ] 4.1 Update `docs/registers/data-sources.md`'s `iso`/`geonames`
      entries: "Consumed by Silver Landing" from "not yet" to "yes",
      naming the new tables
