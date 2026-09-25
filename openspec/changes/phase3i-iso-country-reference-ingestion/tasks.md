## 1. Fetch helper

- [x] 1.1 Created `src/common/iso3166.py` with `fetch_iso3166_csv(url)` —
      HTTP GET, skips `#`-prefixed comment lines, returns parsed CSV rows
- [x] 1.2 Verified the helper against both real files directly (`curl`,
      then Python `requests`) before any pipeline code was written

## 2. Raw ingestion pipeline

- [x] 2.1 Created `src/layers/bronze/iso/country_codes_raw.py` — a
      Materialized View calling the fetch helper against `countries.csv`,
      table comment set to the CC BY-SA 4.0 attribution text, `requests`
      declared as an explicit pipeline environment dependency, stamps
      `ingested_timestamp`
- [x] 2.2 Created `src/layers/bronze/iso/subdivision_codes_raw.py` — same
      pattern against `subdivisions.csv`, renaming
      `subdivision_code_iso3166-2` to `subdivision_code`, stamps
      `ingested_timestamp`
- [x] 2.3 Created `resources/pipelines/iso_country_reference_ingestion.pipeline.yml`
- [x] 2.4 `databricks bundle validate` passed for dev/tst/prd
- [x] 2.5 Deployed and ran against `dev` — confirmed row counts: 249
      (`country_codes_raw`), 6,260 (`subdivision_codes_raw`)
- [x] 2.6 (added during implementation) Created
      `src/layers/bronze/iso/subdivision_codes_quarantine.py` — see task 3
      for why: a real duplicate-key finding, not planned up front

## 3. SCD modeling pipeline

- [x] 3.1 (revised during implementation) No intermediate snapshot
      materialized view created — `create_auto_cdc_from_snapshot_flow`'s
      `source` doesn't need to be a pipeline-internal dataset
      (phase3b-scd-snapshot-cleanup's finding, already established
      project-wide). `country_codes_scd2` reads a `@dp.temporary_view()`
      wrapping `country_codes_raw` directly (stamps `transformed_timestamp`,
      see task 3.3); `subdivision_codes_scd2` reads
      `subdivision_codes_deduped` (private, see below)
- [x] 3.2 **SCD1 dropped from scope** (decided mid-implementation, applies
      to this change and `phase3j-geonames-reference-ingestion` too — see
      design.md). Created `country_codes_scd2.py` (keyed by
      `country_code_alpha2`, confirmed unique via real data) and
      `subdivision_codes_scd2.py` (keyed by `(subdivision_code,
      language_code, subdivision_name)`, **not `subdivision_code` alone** —
      corrected after a real run proved `subdivision_code` alone collides:
      6,260 rows, only 5,046 distinct codes) via
      `create_auto_cdc_from_snapshot_flow`
- [x] 3.3 (added during implementation) Both flows stamp
      `transformed_timestamp` and exclude it plus `ingested_timestamp` via
      `track_history_except_column_list` — ISO is the first source onboarded
      after AirROI introduced this platform pattern (NAMING.md); the
      original design omitted it, corrected here
- [x] 3.4 (added during implementation) Real run hit
      `DUPLICATE_KEY_VIOLATION` on the 3-column key (`RU-DA`/`ru`/`Dagestan`
      — 10 of 6,260 rows are genuine full-row duplicates in the source CSV).
      Fixed with `subdivision_codes_deduped.py` (private, dedupes on the SCD
      key, feeds Auto CDC) and `subdivision_codes_quarantine.py` (task 2.6,
      public, holds the complementary extra rows) — same shape as ACNC's
      quarantine pattern. `raw = distinct_key_count + quarantine_count`
      exactly (6,260 = 6,250 + 10)
- [x] 3.5 Created `resources/pipelines/iso_country_reference_scd_modeling.pipeline.yml`
- [x] 3.6 Deployed and ran against `dev` — `country_codes_scd2`: 249
      current rows (matches `country_codes_raw` exactly).
      `subdivision_codes_scd2`: 6,250 current rows (matches the distinct-key
      count over `subdivision_codes_raw`, not its raw row count of 6,260 —
      expected, per task 3.4)

## 4. Verification suite

- [x] 4.1 Created `verification/verify_iso_country_reference_ingestion.py`
      — row counts, expected columns (including `ingested_timestamp`), the
      `subdivision_code` rename, and `subdivision_codes_quarantine`
      non-empty
- [x] 4.2 Created `verification/verify_iso_country_reference_scd.py` — both
      SCD2 tables' current-row counts against their expected source count,
      plus `raw = distinct_key_count + quarantine_count` for subdivisions
- [x] 4.3 Created `resources/jobs/verify_iso_reference_pattern.job.yml`
- [x] 4.4 Ran against `dev` — both tasks `SUCCESS`

## 5. Documentation

- [x] 5.1 Added a "Sources" entry to CLAUDE.md for ISO 3166 covering the
      pattern, the CC BY-SA 4.0 attribution mechanism, the
      `subdivision_code` rename, the SCD2-only decision, the key
      correction, and the quarantine pattern
- [x] 5.2 Added `bronze/iso/` and `bronze/iso_publish/` to CLAUDE.md's
      repository-structure tree
- [x] 5.3 Created `docs/registers/source_systems/iso.md`, and added an
      entry to `docs/registers/data-sources.md`
- [x] 5.4 (added during implementation) Added a note to NAMING.md's
      "Platform-added timestamp columns" section: every source onboarded
      after AirROI applies the pattern from the start, ISO is the first
- [x] 5.5 (added during implementation) Added Free Edition job/pipeline
      concurrency guidance to CLAUDE.md's "Operational notes" (unrelated to
      ISO specifically, surfaced during this change's implementation)
