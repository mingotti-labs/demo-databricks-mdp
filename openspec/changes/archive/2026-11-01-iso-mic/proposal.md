## Why

The Silver Domain `silver_domain_investments` (change `silver-domain-investments`)
needs a `market` table: every listing is one trading symbol on one market, and
the market is named by its ISO 10383 market identifier code (MIC), for example
`XNYS` for the New York Stock Exchange or `XASX` for the ASX. The user decided
this on 2026-10-31 after asking where a company's exchange or country comes from.
Nothing we hold lists markets. ISO publishes the list free as a CSV at
`https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv`
(2,889 rows: 1,596 operating markets, 1,293 segments, 574 expired). Probes P1 and
P2 (run 2026-10-31, before this proposal) read it and checked the key, the date
format and the encoding.

The Silver Domain reads only `silver_landing`, so the list is ingested first,
up to Silver Landing, as a new table of the existing `iso` source (ISO 3166
countries and subdivisions are there already). The Silver Domain's `market`
table is a separate change that reads it.

## What Changes

- New table in the `iso` source, `market_identifier_codes`, through the same
  three layers as the country codes:
  - **Fetch**: `src/common/iso10383.py` downloads the CSV, decodes the bytes as
    UTF-8 (the server sends no charset and `requests` would guess ISO-8859-1,
    which garbles names such as `ČESKOSLOVENSKÁ OBCHODNÍ BANKA`) and renames the
    17 columns to spelled-out snake_case names.
  - **Bronze raw**: `bronze_iso.market_identifier_codes_raw`, a Materialized
    View that re-fetches the whole file each run (full load, pattern
    `bronze_file_materialized_view_python`), every row kept (operating markets and
    segments, active and expired), values as text, with `ingested_timestamp`.
  - **Bronze Publish**: `bronze_iso_publish.market_identifier_codes_scd2`, SCD2
    by `market_identifier_code` (unique in all 2,889 rows), the bronze full
    pattern.
  - **Silver Landing**: `silver_landing.iso__market_identifier_codes` via
    `land_changes`, with the four date columns as DATE (the user's rule for
    RBA and FRED).
- Column `country_code_alpha2` holds the market's ISO 3166 country code, named
  as in `iso__country_codes` so the two tables join.
- Bundle variable `iso10383_mic_url` in both edition files and the regenerated
  `databricks.yml`.
- Landing and bronze checks: `verification/silver_landing_checks/iso.yml` and
  `verification/bronze_checks/iso.yml` each gain the table.
- Licence: the ISO 10383 terms of use (October 2016) allow free use but not
  reproducing all or a substantial part of the list for third parties. This
  platform uses it internally; the attribution and that limit are a table
  comment on the raw table, and anything that publishes the list (a shared
  dashboard export, say) must not copy it whole.
- **Not in this change**: the `market` table (Silver Domain change), markets for
  non-index benchmarks, ISO 20022 data other than the MIC list.

## Capabilities

### New Capabilities
- `iso-market-identifier-codes`: the ISO 10383 market identifier code list
  ingested into `bronze_iso`, `bronze_iso_publish` and `silver_landing`.

### Modified Capabilities
None. The country reference spec is unchanged; the new table follows its
pattern.

## Impact

- New: `src/common/iso10383.py` with unit tests, `src/layers/bronze/iso/market_identifier_codes_raw.py`,
  `src/layers/bronze/iso_publish/market_identifier_codes_scd2.py`,
  `src/layers/silver/landing/iso/market_identifier_codes.py`.
- Changed: `cicd/databricks/free.yml`, `standard.yml`, `databricks.yml`
  (generated), the `bronze--iso` pipeline resource (one configuration line),
  the two checks files for `iso`, `references/docs/registers/data-sources.md`
  and `design-patterns.md` (the `iso` entries), CLAUDE.md (the ISO entry), the
  probes register.
- Table quota: one Materialized View, one streaming table (Bronze Publish) and
  one streaming table (Landing), 2 slots each, in dev and prd: 12 slots. The
  count was 446 of 500 on 2026-10-31, so about 458 after. `silver-domain-investments`
  adds 36 more, and the two together pass the 488 stop line: a table clean-up
  change must land before the second of them deploys.
- Schema quota: unchanged. No new pipeline: the existing `bronze--iso` and
  `silver--iso` pipelines and the `run_iso` job carry the table.
- Runs: `run_iso` (CI runs it on merge, the source is free and static).

## Cross-repo dependencies

None. `bronze_iso`, `bronze_iso_publish` and `silver_landing` exist in both
catalogs, and the raw table is a Materialized View, so no volume is needed.
`silver-domain-investments` (this repo) depends on this change.

## Model

Sonnet: the change repeats the ISO 3166 ingestion shape (fetch helper, full-load
Materialized View, SCD2, Landing), with the design settled here.
