# portfolio-internal-data Specification

## Purpose
TBD - created by archiving change portfolio-internal-settings. Update Purpose after archive.

## Requirements

### Requirement: Settings are committed CSV files
The curated settings SHALL be committed as CSV files with a header row under
`data/portfolio/`: `concept_mapping.csv`, `predecessor_ciks.csv`,
`settings.csv`, `risk_levels.csv` and `target_mix.csv`. Each file SHALL have a
documented natural key that is unique within the file.

#### Scenario: Keys are unique in the committed files
- **WHEN** the unit tests run
- **THEN** each file parses, has its expected columns, and has no duplicate
  natural key

### Requirement: Copy to the volume on every run
The run job's first task SHALL copy each settings file to
`/Volumes/<catalog>/bronze_portfolio/s3_raw/<dataset>/landing/<dataset>.csv`,
overwriting the previous copy, before the bronze pipeline runs. It SHALL copy
only the five settings files.

#### Scenario: Volume matches the repo after a run
- **WHEN** `run_portfolio` has run in a target
- **THEN** each of the five volume files has the same content as the repo file
  deployed to that target

### Requirement: Bronze raw and SCD2 history
For each dataset, `bronze_portfolio.<dataset>_raw` SHALL be a Materialized View
reading its volume file with every column as text and stamping
`ingested_timestamp`, and `bronze_portfolio_publish.<dataset>_scd2` SHALL be
built in the same pipeline by `create_auto_cdc_from_snapshot_flow` on the
dataset's natural key, following the bronze full pattern (`ingested_timestamp`
left out of the snapshot, `pipelines.reset.allowed` false, change data feed on).

#### Scenario: Current versions equal the file
- **WHEN** the bronze pipeline has run
- **THEN** for each dataset, the SCD2 current-row count equals the raw row
  count, which equals the committed file's row count

#### Scenario: A changed setting is versioned
- **WHEN** one value in a committed file changes and the job runs again
- **THEN** exactly one version is closed and one inserted in that dataset's
  SCD2 table, and the other datasets get no new version

### Requirement: Silver Landing
For each dataset, `silver_landing_portfolio.<dataset>` SHALL be built by the
source's silver pipeline from the SCD2 change feed with `land_changes`, keyed by
the dataset's natural key.

#### Scenario: Landing matches Bronze Publish
- **WHEN** the silver pipeline has run
- **THEN** each Landing table's current rows equal its SCD2 table's current rows

### Requirement: Run job and verification
Job `run_portfolio` SHALL run copy, bronze, then (with `verify=true`)
`verify_bronze` with `source: portfolio`, silver, `verify_silver_landing` with
`source: portfolio`, and the design pattern tags. A change to any settings file
SHALL select `run_portfolio` in CI.

#### Scenario: Verified run passes
- **WHEN** `run_portfolio` is run with `verify=true` in dev
- **THEN** every task succeeds

#### Scenario: Editing a CSV selects the unit
- **WHEN** `cicd/affected_units.py` is given a change to one file in
  `data/portfolio/`
- **THEN** it selects the `portfolio` unit
