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
  into SCD1/SCD2
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

**SCD1 + SCD2 built for both tables, matching the SCD2 > SCD1 > SCD0
precedence rule** (`docs/medallion/silver.md`) even though this is
low-change-frequency reference data — cheap to build, and SCD2 gives a
real audit trail on the rare occasion a country/subdivision code does
change (e.g. a country splits, a subdivision is renamed). Keyed by
`country_code_alpha2` (countries) and `subdivision_code` (subdivisions).

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
