## Context

See proposal.md - Why. Confirmed via real fetches before any design work
started, against `download.geonames.org/export/dump/`:

- `countryInfo.txt` — tab-delimited, `#`-comment header lines, 252 data
  rows (more than ISO 3166-1's 249 — GeoNames includes some non-ISO
  entities, e.g. disputed/dependent territories; not a discrepancy to
  "fix," just a real difference between the two sources).
- `admin1CodesASCII.txt` — 3,865 rows: `code` (GeoNames' own scheme, e.g.
  `AD.06`), `name`, `asciiname`, `geonameId`.
- `admin2Codes.txt` — 47,643 rows: `code` (concatenated
  country.admin1.admin2), `name`, `asciiname`, `geonameId`.
- `cities500.zip` — 13.86MB compressed, one tab-delimited file inside using
  GeoNames' documented 19-column "geoname" table shape (geonameId, name,
  asciiname, alternatenames, latitude, longitude, feature class, feature
  code, country code, cc2, admin1 code, admin2 code, admin3 code, admin4
  code, population, elevation, dem, timezone, modification date), per
  `download.geonames.org/export/dump/readme.txt`.

## Goals / Non-Goals

**Goals:**
- A working, verified ingestion of all four files into `bronze_geonames`,
  modeled into SCD1/SCD2
- CC BY 4.0 attribution recorded on the tables themselves

**Non-Goals:**
- `cities1000`/`cities5000`/`cities15000`/`allCountries` — larger
  population-threshold variants (up to ~12M rows for `allCountries`).
  `cities500` is the smallest official variant and already covers every
  real locality this project's sources touch (Australia, Brazil, New
  Zealand markets are all well above a 500-population threshold); scaling
  up is a later, separate decision if a genuinely finer-grained lookup is
  needed, not a default to reach for now.
- `alternateNamesV2.zip` (multi-language name variants) — not needed for
  the country/state/city backbone itself; a plausible future addition, not
  scoped now.
- Reconciling GeoNames' own admin1/admin2 code scheme (e.g. `AD.06`)
  against ISO 3166-2 codes (e.g. `AD-07`) — confirmed these are different,
  non-interchangeable code schemes (see
  `phase3i-iso-country-reference-ingestion`'s design.md). This is exactly
  the kind of cross-source reconciliation the future GenAI-assisted
  normalization work (see the planning repo's brainstorm note) is meant to
  solve — not something to hand-roll here in bronze.

## Decisions

**Two small helper functions, not a generic dump-file framework.**
`fetch_geonames_dump(url)` for the three plain tab-delimited files,
`fetch_geonames_zip_dump(url, inner_filename)` for the one zip-wrapped
file (`zipfile` + `io.BytesIO`, extracting the one inner `.txt` file by
name) — both driver-side fetches, matching UNGM's "trivially small enough
for a driver-side fetch + `spark.createDataFrame`" reasoning. `cities500`
at ~14MB compressed is an order of magnitude larger than UNGM's ~1.4MB but
still well within a single-shot driver-side fetch; no custom Spark
DataSource or distributed/partitioned reader is needed since these are
flat files, not a paginated API (that complexity belongs to ACNC's/NSW
Spatial's connector pattern, which doesn't apply here).

**Four Materialized Views, full-refresh, matching ISO's pattern.** None of
these files expose an incremental cursor; GeoNames publishes them as
complete daily snapshots, so full-refresh batch pull is correct, not a
workaround.

**Table names don't encode the `500` population threshold.** `cities_raw`,
not `cities500_raw` — the threshold is a source-selection detail (recorded
here and in the table comment), not part of the entity's identity, matching
`unspsc_public_raw` not encoding UNGM's pagination scheme in its name.

**SCD1 + SCD2 built for all four tables**, same reasoning as ISO's:
cheap to build, gives a real audit trail on population/name corrections.
Keyed by `iso_alpha2` for `country_info`, `code` for `admin1_codes` and
`admin2_codes`, `geonameid` for `cities`.

**License attribution as a Unity Catalog table comment**, same mechanism
as ISO's, using GeoNames' CC BY 4.0 attribution requirement.

## Risks / Trade-offs

- [`cities_raw` at ~200K+ rows is meaningfully larger than every other
  reference table in this change, making its SCD2 snapshot-comparison the
  most expensive of the four] → Mitigation: accepted — this is still a
  batch reference dataset refreshed on-demand, not a per-minute pipeline;
  Free Edition serverless quota is the real constraint (see this repo's
  `RESOURCE_EXHAUSTED` note in CLAUDE.md) — space this pipeline's runs
  rather than running it concurrently with others, same discipline already
  established for Silver Landing's deployment.
- [GeoNames' admin1/admin2 codes don't map cleanly onto ISO 3166-2] →
  Mitigation: explicitly out of scope here (see Non-Goals); this is the
  actual justification for the future GenAI-normalization app the planning
  brainstorm describes, not a gap to quietly work around now.

## Migration Plan

Depends on `demo-databricks-iac`'s `phase3j-geonames-schema` landing first
(itself depending on `phase3i-iso-schema` — see that change's proposal.md).
Deploy to `dev`, verify via `verify_geonames_reference_pattern`, then
promote to `tst`/`prd`, spacing pipeline runs to avoid the known serverless
quota issue. Rollback: remove the resources from the bundle; full-refresh
only, no destructive state involved.
