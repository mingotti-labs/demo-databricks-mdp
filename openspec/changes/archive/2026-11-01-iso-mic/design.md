## Context

The `iso` source holds ISO 3166 countries and subdivisions: `bronze--iso--<target>`
(raw Materialized Views in `bronze_iso`, SCD2 in `bronze_iso_publish`),
`silver--iso--<target>` (Landing via `land_changes`) and job `run_iso`. Probes
P1 and P2 (2026-10-31, `references/poc/iso-mic/`) read the ISO 10383 CSV:

| Finding | Value |
|---|---|
| Rows | 2,889: 1,596 `OPRT` (operating markets), 1,293 `SGMT` (segments) |
| Status | 2,313 `ACTIVE`, 574 `EXPIRED`, 2 `UPDATED` |
| Key | `MIC` is unique in all 2,889 rows; no quarantine table is needed |
| Dates | `YYYYMMDD` text; `LAST VALIDATION DATE` filled in 996 rows, `EXPIRY DATE` in 576, the other two in all |
| Encoding | UTF-8, no BOM, `content-type: text/csv` with no charset; `requests` guesses ISO-8859-1 from `response.text`, which garbles accents |
| Operating rows | every `OPRT` row has `OPERATING MIC` equal to its own `MIC` |
| Orphans | 8 rows name an operating MIC that has no `OPRT` row; all are expired segments (`XEAS`, `ICAT`, `EXPA`, `NBXO`, `THRD`, `PCDS`, `VRXP`, `LIQH`) |
| Country | `ISO COUNTRY CODE (ISO 3166)` is filled on every row |

The metastore held 446 of 500 table slots on 2026-10-31; the working stop line
is 488.

## Goals / Non-Goals

**Goals:**
- The whole list, current and past versions, in Landing with the same
  lineage columns as the other `iso` tables.
- Nothing that fails silently: a renamed column fails the fetch.

**Non-Goals:**
- Choosing which rows are markets (operating only) or which are current: the
  Silver Domain `market` table does that.
- A raw volume or append-only raw: the file is small and full, like the ISO 3166
  files, so a full-load Materialized View is the right shape.

## Decisions

### Same shape as ISO 3166, no new pipeline
The raw Materialized View joins `bronze--iso`, its SCD2 table joins the same
pipeline, its Landing table joins `silver--iso`, and `run_iso` stays as it is.
Alternative: a separate `iso_mic` source with its own pipelines and job.
Rejected: it costs two pipelines of schema and quota overhead for one table, and
the list is ISO reference data like the country codes.

### Fetch decodes bytes as UTF-8
`fetch_market_identifier_codes(url)` uses `response.content.decode("utf-8")`,
never `response.text`. Probe P2: the file decodes as UTF-8 and fails as
cp1252, and `requests` would have guessed ISO-8859-1. A new function in
`src/common/iso10383.py`, not a change to `iso3166.py`: that helper strips a
leading `#` and its raw URLs are text/plain from GitHub, which already decodes
correctly.

### Spelled-out column names
No abbreviations (user, 2026-10-31, for the domain layer; applied here so the
Silver Domain only selects):

| Source column | Column |
|---|---|
| `MIC` | `market_identifier_code` |
| `OPERATING MIC` | `operating_market_identifier_code` |
| `OPRT/SGMT` | `operating_or_segment` (values stay `OPRT` and `SGMT`) |
| `MARKET NAME-INSTITUTION DESCRIPTION` | `market_name` |
| `LEGAL ENTITY NAME` | `legal_entity_name` |
| `LEI` | `legal_entity_identifier` |
| `MARKET CATEGORY CODE` | `market_category_code` |
| `ACRONYM` | `acronym` |
| `ISO COUNTRY CODE (ISO 3166)` | `country_code_alpha2` (as in `iso__country_codes`) |
| `CITY`, `WEBSITE`, `STATUS`, `COMMENTS` | `city`, `website`, `status`, `comments` |
| `CREATION DATE`, `LAST UPDATE DATE`, `LAST VALIDATION DATE`, `EXPIRY DATE` | `creation_date`, `last_update_date`, `last_validation_date`, `expiry_date` |

The fetch fails if a source column is missing, so an upstream rename is a loud
failure, not empty columns.

### SCD2 key and history
`market_identifier_code` is the key (unique, probe P1). ISO changes a market's
status, name or expiry over time, and the SCD2 versions keep that. The CSV's own
`LAST UPDATE DATE` is data, not a version marker, so it stays a column; the
bronze full pattern's versions come from the pipeline update's time, as for the
country codes.

### Dates in Landing, text elsewhere
`creation_date`, `last_update_date`, `last_validation_date` and `expiry_date`
become DATE in Landing with `to_date(value, 'yyyyMMdd')`, null where empty. Raw
and Publish keep the text as the file has it, as for RBA and FRED.

### Licence
ISO 10383's terms (October 2016) grant a non-exclusive right to access and use
the information and exclude reproducing all or a substantial part of the site
for making it available to third parties. Internal analytics is within that.
The raw table's comment names the source and states the limit
(`ATTRIBUTION`, as the ISO 3166 raw tables do for CC BY-SA). Consequence for
later changes: the `market` table and gold may select what a listing needs, but a
public export of the whole list is out.

## Risks / Trade-offs

- [The URL moves or the file changes shape] → the fetch fails loudly; the
  variable `iso10383_mic_url` is one line to change in both edition files.
- [ISO adds a column] → ignored by name (the fetch keeps the 17 named columns
  only); a new column would be a deliberate change.
- [Expired segments whose operating market is gone] → kept in Landing as the
  source has them; the Silver Domain `market` selects operating rows, which have
  no such gap (probe P2).
- [Table quota: 12 slots, about 458 after] → `silver-domain-investments`
  adds 36 and passes the 488 stop line, so a clean-up change must land before the
  second of the two deploys. Candidates: the dev-only pattern pipelines' tables,
  the human-owned neon and clickstream dev copies (15 tables), orphan
  materialization twins.

## Migration Plan

1. Merge the proposal.
2. Implementation PR: fetch helper and tests, the three table files, the bundle
   variable, checks files; draft PR deploys to dev; `run_iso` as the service
   principal with `verify=true`.
3. Merge: CI runs `run_iso` in prd (after the user approves the prd
   environment); check the counts match dev.

Rollback: remove the three table files and the variable; the tables are dropped
with the pipeline update (a `bronze_iso_publish` SCD2 table cannot be removed by
a refresh, so the drop is done by the user with approval, and the hidden
materialization twins with it).

## Dev results (2026-10-31)

`run_iso` as the service principal with `verify=true` (draft PR #131):
- First run succeeded. Raw, Publish and Landing each hold 2,889 rows, 1,596 of
  them `OPRT`; 2,889 current versions in Publish.
- Landing: `XASX` has country `AU`, `XTKS` has operating market `XJPX` and
  country `JP`, `CSOB` has country `CZ` and its name starts with `Č`. The four
  date columns are DATE; 576 rows have an `expiry_date`, 2,313 have none (null),
  matching the file.
- Second run succeeded with no source change: Publish still has 2,889 rows, all
  current (no spurious versions).
- `verify_silver_landing` with an empty `source` verified 32 entities (31 before).
- Table quota before the first run: 446 of 500.

## Prd results (2026-11-01)

- The prd Main run for PR #131 failed for `iso` (and for `geonames`, `portfolio`
  and `sec`) with the platform error INTERNAL_ERROR_BEHAVIOR_CHANGED
  (`sessionConfigChanged`), not with code: `iso`'s bronze task had passed and its
  silver task was paused by the platform. A rerun of `run--iso--prd` by job id
  succeeded.
- `mdp_prd`: raw, Publish and Landing each hold 2,889 rows, 1,596 `OPRT`, 576
  with an `expiry_date`; 0 rows differ from dev Landing on key, operating
  market, status, country, dates and name.
- The Main run started ten units because CI takes the last successful Main run as
  its base, and the FRED run before it had failed the same way; the diff since
  the RBA run covered every change since.
- Table quota: 456 of 500 after the run.
