## ADDED Requirements

### Requirement: Constituents fetch helper
`src/common/wikipedia_sp500.py` SHALL provide a function that fetches the
Wikipedia "List of S&P 500 companies" page with a `User-Agent` header, parses
the table with id `constituents` and returns rows with snake_case column names
and every value as text, with CIK zero-padded to 10 digits.

#### Scenario: Helper parses the real page
- **WHEN** the helper is called against the real page
- **THEN** it returns about 500 rows (at least 480) with the columns `symbol`,
  `security`, `gics_sector`, `gics_sub_industry`, `headquarters_location`,
  `date_added`, `cik` and `founded`, and every `cik` has 10 digits

### Requirement: Full-refresh ingestion into bronze_wikipedia
`sp500_constituents_raw` SHALL be a Materialized View that re-fetches the
complete table on every run and stamps `ingested_timestamp`. Values SHALL be
kept as the source gives them (symbols keep their dots, dates stay text).

#### Scenario: Pipeline run lands the index
- **WHEN** the bronze pipeline runs
- **THEN** `<catalog>.bronze_wikipedia.sp500_constituents_raw` has at least 480
  rows, no null `symbol`, and a populated `ingested_timestamp`

### Requirement: Membership history as SCD2
`sp500_constituents_scd2` SHALL exist in `bronze_wikipedia_publish`, built by
the source's bronze pipeline with `create_auto_cdc_from_snapshot_flow` keyed by
`symbol`, following the bronze full pattern: `ingested_timestamp` is excluded
from the snapshot, `pipelines.reset.allowed` is `false` and the change data feed
is enabled. A company that disappears from the page SHALL have its current
version closed, and one that appears SHALL get a new version.

#### Scenario: Current versions equal the raw list
- **WHEN** the bronze pipeline has run
- **THEN** the count of `sp500_constituents_scd2` rows with `__END_AT IS NULL`
  equals the raw row count

#### Scenario: Unchanged rerun writes nothing
- **WHEN** the bronze pipeline runs again with no change on the page
- **THEN** no version is inserted or closed

### Requirement: Silver Landing
`silver_landing_wikipedia.sp500_constituents` SHALL be built by the source's
silver pipeline from the SCD2 table's change feed (`land_changes`), with
`symbol` as the natural key and the platform conventions of Silver Landing.

#### Scenario: Landing matches Bronze Publish
- **WHEN** the silver pipeline has run
- **THEN** Landing has one row per SCD2 version and its current rows equal the
  SCD2 table's current rows

### Requirement: Run job and verification
Job `run_wikipedia` SHALL run bronze, then (with `verify=true`) `verify_bronze`
with `source: wikipedia`, then silver, then `verify_silver_landing` with
`source: wikipedia`.

#### Scenario: Verified run passes
- **WHEN** `run_wikipedia` is run with `verify=true` in dev
- **THEN** every task succeeds
