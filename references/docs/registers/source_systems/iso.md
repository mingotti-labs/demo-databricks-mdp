# ISO 3166 Country/Subdivision Reference Data

ISO 3166-1 (country codes) and ISO 3166-2 (subdivision codes), via a public,
unauthenticated GitHub CSV mirror. Free, no auth. The smallest ingestion
pattern in the project — two static files, no pagination, no WAF block.

- Base URL: `raw.githubusercontent.com/ipregistry/iso3166/master/` —
  `countries.csv` and `subdivisions.csv`, same for every target (no
  test/prod split needed for this source).
- Auth: none — public files.
- License: CC BY-SA 4.0 (ipregistry's own repo). Attribution text is set as
  a Unity Catalog table `comment` on both `_raw` tables at creation, not
  just a docs note — the first externally-*licensed* (not just
  externally-sourced) dataset in this project.
- Code: `src/common/iso3166.py` (small, source-scoped fetch helper),
  `src/layers/bronze/iso/country_codes_raw.py`/`subdivision_codes_raw.py`/
  `subdivision_codes_quarantine.py`,
  `src/layers/bronze/iso_publish/country_codes_scd2.py`/
  `subdivision_codes_scd2.py`/`subdivision_codes_deduped.py` (private).

## Ingestion in this project

Both `bronze_iso.country_codes_raw`/`subdivision_codes_raw` are Materialized
Views that re-fetch the whole file each run — no pagination or incremental
cursor exists for either file, confirmed via real requests (249 and 6,260
rows respectively) before any code was written.

- `subdivision_code_iso3166-2` is renamed to `subdivision_code` on ingest —
  the source column name's hyphen isn't a valid Spark column identifier on
  its own, and the schema name already implies "ISO 3166-2."
- **SCD2-only, no SCD1** — a scope decision, not a technical necessity:
  low-change-frequency reference data doesn't need a separate "latest
  value" table when SCD2's `WHERE __END_AT IS NULL` gives the same thing.
- Both `_raw` tables stamp `ingested_timestamp`; both SCD2 flows stamp
  `transformed_timestamp` in an intermediate dataset just ahead of Auto
  CDC, both excluding both timestamp columns via
  `track_history_except_column_list` — same pattern as AirROI's (see
  NAMING.md's "Platform-added timestamp columns"). ISO is the first source
  onboarded *after* AirROI, so it applies the pattern from the start rather
  than needing a later retrofit.

## SCD key correction (subdivisions)

`country_code_alpha2` is a clean SCD key for `country_codes_scd2` — 249
distinct values across 249 rows, confirmed via the real source data.

`subdivision_code` alone is **not** a clean key for subdivisions — confirmed
via a real pipeline failure, not assumed from the CSV's column names. Same
category of finding as NSW Spatial's `addressstringoid`-vs-`propid`
correction: caught empirically, fixed before merging, not before running.

- 6,260 rows but only 5,046 distinct `subdivision_code` values: a
  subdivision can carry more than one localized name (e.g. `AF-BDS` has
  separate Dari/`fa` and Pashto/`ps` names for the same Afghan province).
- Adding `language_code` still leaves 175 collisions — different
  transliterations of the same name in the same language (e.g. `BY-BR`'s
  "Bresckaja voblasć" vs. "Brestskaya voblasts'", both tagged `be`).
- `(subdivision_code, language_code, subdivision_name)` together fully
  partition the data — confirmed zero inconsistency in the remaining
  columns within any group sharing this 3-column key.

Even the corrected 3-column key isn't quite enough on its own:
`create_auto_cdc_from_snapshot_flow` still hit
`DUPLICATE_KEY_VIOLATION` on a real run (`RU-DA`/`ru`/`Dagestan`) — 10 of
6,260 rows are genuine full-row duplicates in the source CSV itself,
confirmed byte-identical. Auto CDC's snapshot flow rejects more than one
row per key outright, with zero tolerance for identical duplicates.

## Quarantine pattern (subdivisions)

Same shape as ACNC's charity register quarantine: rather than silently
dropping the 10 duplicate rows inside the SCD pipeline, two datasets read
the same `subdivision_codes_raw` with complementary logic, using a
`row_number()` window over the SCD key —

- `subdivision_codes_deduped` (private, `bronze_iso_publish`): rank 1 per
  key, feeds `subdivision_codes_scd2`'s `create_auto_cdc_from_snapshot_flow`.
- `subdivision_codes_quarantine` (public, `bronze_iso`): rank > 1 per key,
  kept visible and queryable rather than discarded.

`raw = distinct_key_count + quarantine_count` exactly (6,260 = 6,250 + 10),
checked by `verify_iso_country_reference_scd.py`.
