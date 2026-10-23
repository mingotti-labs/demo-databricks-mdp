## ADDED Requirements

### Requirement: Every full-load source follows the bronze full pattern
Every source whose `_raw` table is a full load SHALL build its Bronze Publish
SCD2 table with snapshot Auto CDC from a snapshot that excludes every column
that changes on each load, with change data feed on, and SHALL build its Silver
Landing as a streaming table over that change feed.

#### Scenario: Second load with no source change
- **WHEN** a source is loaded twice and no business column changed
- **THEN** the second load writes 0 rows to its SCD2 table and to its Landing
  tables

### Requirement: Landing carries the version's fetch time
Silver Landing SHALL set `ingested_timestamp` to the SCD2 version's `__START_AT`
for every source, whether or not its `_raw` table stamps one.

#### Scenario: Source without a raw stamp
- **WHEN** a source's `_raw` table has no `ingested_timestamp`
- **THEN** its Landing rows still have `ingested_timestamp` equal to `scd_valid_from_timestamp`
