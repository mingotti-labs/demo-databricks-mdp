## 1. Fetch helper

- [ ] 1.1 Created `src/common/iso3166.py` with `fetch_iso3166_csv(url)` —
      HTTP GET, skips `#`-prefixed comment lines, returns parsed CSV rows
- [ ] 1.2 Verified the helper against both real files directly (`curl`,
      then Python `requests`) before any pipeline code was written

## 2. Raw ingestion pipeline

- [ ] 2.1 Created `src/layers/bronze/iso/country_codes_raw.py` — a
      Materialized View calling the fetch helper against `countries.csv`,
      table comment set to the CC BY-SA 4.0 attribution text, `requests`
      declared as an explicit pipeline environment dependency
- [ ] 2.2 Created `src/layers/bronze/iso/subdivision_codes_raw.py` — same
      pattern against `subdivisions.csv`, renaming
      `subdivision_code_iso3166-2` to `subdivision_code`
- [ ] 2.3 Created `resources/pipelines/iso_country_reference_ingestion.pipeline.yml`
- [ ] 2.4 `databricks bundle validate` passed for dev/tst/prd
- [ ] 2.5 Deployed and ran against `dev` — confirmed row counts: 249
      (`country_codes_raw`), 6,260 (`subdivision_codes_raw`)

## 3. SCD modeling pipeline

- [ ] 3.1 Created `src/layers/bronze/iso_publish/country_codes_snapshot.py`
      and `subdivision_codes_snapshot.py` (batch snapshots of each `_raw`
      table)
- [ ] 3.2 Created `country_codes_scd1.py`/`country_codes_scd2.py` (keyed by
      `country_code_alpha2`) and
      `subdivision_codes_scd1.py`/`subdivision_codes_scd2.py` (keyed by
      `subdivision_code`) via `create_auto_cdc_from_snapshot_flow`
- [ ] 3.3 Created `resources/pipelines/iso_country_reference_scd_modeling.pipeline.yml`
- [ ] 3.4 Deployed and ran against `dev` — SCD table row counts match
      their `_raw` counterpart exactly

## 4. Verification suite

- [ ] 4.1 Created `verification/verify_iso_country_reference_ingestion.py`
- [ ] 4.2 Created `verification/verify_iso_country_reference_scd.py`
- [ ] 4.3 Created `resources/jobs/verify_iso_reference_pattern.job.yml`
- [ ] 4.4 Ran against `dev` — all tasks `SUCCESS`

## 5. Documentation

- [ ] 5.1 Added a "Sources" entry to CLAUDE.md for ISO 3166 covering the
      pattern, the CC BY-SA 4.0 attribution mechanism, and the
      `subdivision_code` rename
- [ ] 5.2 Added `bronze/iso/` and `bronze/iso_publish/` to CLAUDE.md's
      repository-structure tree
- [ ] 5.3 Created `docs/registers/source_systems/iso.md`, and added an
      entry to `docs/registers/data-sources.md`
