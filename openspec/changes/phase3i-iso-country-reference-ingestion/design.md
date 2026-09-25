## Context

See proposal.md - Why. Confirmed via real fetches before any design work
started, against `raw.githubusercontent.com/ipregistry/iso3166/master/`:

- `countries.csv` — header `#country_code_alpha2,country_code_alpha3,
  numeric_code,name_short,name_long`, 249 data rows.
- `subdivisions.csv` — header `#country_code_alpha2,
  subdivision_code_iso3166-2,subdivision_name,language_code,
  parent_subdivision,category,localVariant`, 6,260 data rows.

Both returned `200` with no WAF/User-Agent block — unlike `iso.org`
itself, which returned a real `403` to a direct fetch. The data isn't
copyrightable in the way the standard's narrative document is, so the
mirror is a legitimate, practical substitute for the gated official source
— same reasoning that made GeoNames (not a gated national G-NAF-style
source) the right pick for city/locality.

## Goals / Non-Goals

**Goals:**
- A working, verified ingestion of both files into `bronze_iso`, modeled
  into SCD2
- CC BY-SA 4.0 attribution recorded on the tables themselves, not just in
  repo docs — this is externally-licensed data, not project-generated

**Non-Goals:**
- ISO 4217 (currency) or other ISO standards — not asked for, not needed
  by any current source (AirROI's `currency` field is a free-text/enum
  value from AirROI itself, not currently joined against a reference
  table); a future addition under the same `bronze_iso` schema, not scoped
  now
- Mapping GeoNames' own admin1 code scheme (e.g. `AD.06`) to ISO 3166-2
  codes (e.g. `AD-07`) — confirmed these are different code schemes, not
  interchangeable strings; reconciling them is a Silver-layer normalization
  concern, out of scope for bronze ingestion of either source
- SQL SCD1/SCD2 — a deliberate scope decision matching UNGM's precedent,
  not a technical necessity
- SCD1 (Python or SQL) — dropped from scope during implementation (see
  Decisions); this and `phase3j-geonames-reference-ingestion` are SCD2-only

## Decisions

**A single small fetch helper, not a generic CSV-source connector.**
Unlike ACNC/NSW Spatial (which needed reusable custom Spark DataSource
connectors for paginated APIs), both ISO files are single static
downloads with no pagination — `fetch_iso3166_csv(url)` is a plain
`requests.get()` + `csv.DictReader`, matching UNGM's "small,
source-scoped fetch helper" pattern, not ACNC's/NSW's connector pattern.
This is the smallest ingestion pattern in the project so far.

**Materialized Views, full-refresh, for both `_raw` tables.** Neither
source has pagination or an incremental cursor — same reasoning as UNGM's
`unspsc_public_raw`. At 249 and 6,260 rows respectively, full-refresh is
trivially cheap.

**`subdivision_code_iso3166-2` renamed to `subdivision_code` on ingest.**
The source CSV's own column name contains a hyphen, which needs sanitizing
for a Spark DataFrame column identifier; the schema already implies "ISO
3166-2" via the table name, so the shorter name is used rather than
`subdivision_code_iso3166_2`.

**SCD2 only, no SCD1 — revised during implementation.** The original plan
built both variants, matching the SCD2 > SCD1 > SCD0 precedence rule
(`docs/medallion/silver.md`). Decided instead, before implementation
finished, that SCD1 is redundant for this kind of low-change-frequency
reference data: SCD2's `WHERE __END_AT IS NULL` already gives the "latest
value" view SCD1 would provide, so a separate table just duplicates that
filter. Applies to this change and `phase3j-geonames-reference-ingestion`.

**`country_codes_scd2` keyed by `country_code_alpha2`** — confirmed unique
(249 distinct of 249 rows) via the real source data.

**`subdivision_codes_scd2` keyed by `(subdivision_code, language_code,
subdivision_name)`, not `subdivision_code` alone — corrected during
implementation, not assumed from the original design.** A real pipeline
run proved `subdivision_code` alone is not unique: 6,260 rows but only
5,046 distinct codes, because a subdivision can carry more than one
localized name (e.g. `AF-BDS` has separate Dari/`fa` and Pashto/`ps` names
for the same Afghan province). Adding `language_code` alone still leaves
175 collisions — different transliterations of the same name in the same
language (e.g. `BY-BR`'s "Bresckaja voblasć" vs. "Brestskaya voblasts'",
both tagged `be`). The 3-column composite key was confirmed, empirically,
to fully partition the data with zero inconsistency in the remaining
columns per group. Same category of finding as NSW Spatial's
`addressstringoid`-vs-`propid` key correction — caught via real data, not
assumed from the CSV's column names.

**Quarantine pattern added for subdivisions, same shape as ACNC's.** Even
the corrected 3-column key wasn't enough on its own:
`create_auto_cdc_from_snapshot_flow` hit a real `DUPLICATE_KEY_VIOLATION`
(`RU-DA`/`ru`/`Dagestan`) — 10 of 6,260 rows are genuine full-row
duplicates in the source CSV, confirmed byte-identical, which Auto CDC's
snapshot flow rejects outright with zero tolerance. Rather than silently
dropping the extras inside the dedup step, two datasets read the same
`subdivision_codes_raw` with complementary `row_number()`-window logic:
`subdivision_codes_deduped` (private, rank 1 per key, feeds Auto CDC) and
`subdivision_codes_quarantine` (public, in `bronze_iso`, rank > 1 per key).
`raw = distinct_key_count + quarantine_count` exactly (6,260 = 6,250 + 10).

**`ingested_timestamp`/`transformed_timestamp` added — not part of the
original design, corrected during implementation.** ISO is the first
source onboarded after AirROI (Phase 3h) introduced these two platform
lineage columns (NAMING.md); the original design omitted them, which was
an oversight rather than a considered exclusion — every source onboarded
after AirROI should apply the pattern from the start, not just sources
that are later revisited. Both `_raw` tables stamp `ingested_timestamp`;
both SCD2 flows stamp `transformed_timestamp` in an intermediate dataset
immediately upstream of Auto CDC (a `@dp.temporary_view()` for
`country_codes_scd2`, folded into the already-necessary
`subdivision_codes_deduped` private view for subdivisions), excluding both
columns via `track_history_except_column_list` — same pattern as AirROI's
`market_summary_scd2.py`.

**License attribution as a Unity Catalog table comment.** CC BY-SA 4.0
requires attribution wherever the data is used; the ipregistry repo's own
required text ("This site or product includes Ipregistry ISO 3166 data
available from https://ipregistry.co.") is set as the `comment` on both
`_raw` tables at creation, not left as a docs-only note — the first
externally-licensed (not just externally-sourced) dataset in this project.

## Risks / Trade-offs

- [The GitHub mirror is a third-party republication of ISO 3166 data, not
  ISO's own distribution] → Mitigation: accepted — ISO 3166 codes/names are
  short factual data (not the copyrightable standard document itself), and
  the mirror is a widely-used, actively-maintained repo; re-confirm the
  mirror is still live/accurate at implementation time, same discipline as
  every other source's "confirmed via a real request" standard.
- [GeoNames' admin1 codes don't match ISO 3166-2 codes directly] →
  Mitigation: explicitly out of scope here (see Non-Goals); recorded so the
  future Silver normalization work isn't surprised by it.

## Migration Plan

Depends on `demo-databricks-iac`'s `phase3i-iso-schema` landing first (see
proposal.md's cross-repo dependencies). Deploy to `dev`, verify via
`verify_iso_reference_pattern`, then promote to `tst`/`prd`. Rollback:
remove the resources from the bundle; full-refresh only, no destructive
state involved.
