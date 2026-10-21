# GeoNames Country/Admin1/Admin2/City Gazetteer

GeoNames' country, subdivision (admin1/admin2), and city gazetteer data,
via public, unauthenticated static dump files. Free, no auth. The
city/locality half of the authoritative reference-data backbone, sitting
under ISO 3166's country/state half (`docs/registers/source_systems/iso.md`).

- Base URL: `download.geonames.org/export/dump/` — `countryInfo.txt`,
  `admin1CodesASCII.txt`, `admin2Codes.txt` (plain tab-delimited), and
  `cities500.zip` (zip-wrapped) — same for every target (no test/prod
  split needed).
- Auth: none — public files.
- License: CC BY 4.0. Attribution text is set as a Unity Catalog table
  `comment` on all four `_raw` tables at creation, same mechanism as ISO's.
- Code: `src/common/geonames.py` (`fetch_geonames_dump`,
  `fetch_geonames_zip_dump`),
  `src/layers/bronze/geonames/country_info_raw.py`/`admin1_codes_raw.py`/
  `admin2_codes_raw.py`/`cities_raw.py`,
  `src/layers/bronze/geonames_publish/country_info_scd2.py`/
  `admin1_codes_scd2.py`/`admin2_codes_scd2.py`/`cities_scd2.py`.

## Ingestion in this project

All four `_raw` tables are Materialized Views that re-fetch their complete
source file each run — none of these files expose an incremental cursor,
confirmed via real fetches (252 / 3,865 / 47,643 / 235,878 rows) before any
code was written.

- **No file gives `csv.DictReader` a usable header row.** `admin1CodesASCII.txt`,
  `admin2Codes.txt`, and `cities500.txt` have no header at all; `countryInfo.txt`'s
  real header (`#ISO	ISO3	...`) is one of several `#`-prefixed documentation
  lines, not reliably the first or last. Both fetch helpers take `fieldnames`
  explicitly rather than trying to parse a header out of the file.
- **`cities500.zip`** (~14MB compressed, 235,878 rows) is an order of
  magnitude larger than UNGM's ~1.4MB fetch, but still a single
  driver-side `requests.get()` + in-memory `zipfile` extraction — no custom
  Spark DataSource or partitioned reader needed, since this is a flat file,
  not a paginated API.
- **Table names don't encode the `500` population threshold** —
  `cities_raw`, not `cities500_raw` — the threshold is a source-selection
  detail (recorded in the table comment), not part of the entity's
  identity, matching `unspsc_public_raw` not encoding UNGM's pagination
  scheme in its name.

## SCD keys — verified before implementation, not assumed

All four SCD keys were checked for uniqueness against the real fetched
data *before* any SCD pipeline code was written — the proactive check
ISO's `subdivision_code` surprise
(`docs/registers/source_systems/iso.md`) motivated:

| Table | Key | Distinct / Total |
|---|---|---|
| `country_info` | `iso_alpha2` | 252 / 252 |
| `admin1_codes` | `code` | 3,865 / 3,865 |
| `admin2_codes` | `code` | 47,643 / 47,643 |
| `cities` | `geonameid` | 235,878 / 235,878 |

All four held up — no quarantine table exists for any GeoNames table,
unlike ISO's `subdivision_codes_quarantine`.

## Platform timestamps

`ingested_timestamp` on each `_raw` table; `transformed_timestamp` stamped
at the SCD2 layer via a `@dp.temporary_view()` per table; both excluded via
`track_history_except_column_list` so a rerun with no real source change
creates no spurious SCD2 history — same pattern as ISO's and AirROI's. Done
from the start here, unlike ISO's change which added it as a mid-implementation
correction.

## SCD2-only, no SCD1

Same scope decision as `phase3i-iso-country-reference-ingestion`'s (made
mid-implementation there, applied here from the start): low-change-frequency
reference data doesn't need a separate "latest value" table when SCD2's
`WHERE __END_AT IS NULL` gives the same thing.
