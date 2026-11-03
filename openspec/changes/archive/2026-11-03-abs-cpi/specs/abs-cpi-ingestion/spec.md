## ADDED Requirements

### Requirement: Series fetched
Each run SHALL fetch every series named in the ABS series list from the ABS Data API
at the address in the bundle variable `abs_api_url`, dataflow `ABS,CPI,2.0.0`, with
no key. The list SHALL hold the all-groups CPI for Australia, original:
`1.10001.10.50.Q` (quarterly) and `1.10001.10.50.M` (monthly). Each run SHALL request
every observation of each series.

#### Scenario: The quarterly CPI is fetched
- **WHEN** `run_abs` runs
- **THEN** rows exist for `series_key` `1.10001.10.50.Q` from `time_period` `1948-Q3`

#### Scenario: The monthly CPI is fetched
- **WHEN** `run_abs` runs
- **THEN** rows exist for `series_key` `1.10001.10.50.M` from `time_period` `2024-04`

#### Scenario: A request fails
- **WHEN** the ABS answers a request with an error status, or with no records
- **THEN** the fetch task fails with the series key and the status, and writes no file
  for that run

### Requirement: Observation rows
Each row SHALL hold:
- `series_key` (`MEASURE.INDEX.TSEST.REGION.FREQ`) and `time_period` as the ABS sent
  it;
- `value`, the observation value as text;
- the labels `measure`, `index`, `adjustment_type`, `region`, `frequency`, `unit` and
  `base_period`;
- `obs_status`;
- `ingested_timestamp`, the fetch time.

Rows with no observation value SHALL be skipped.

#### Scenario: A quarter
- **WHEN** the ABS returns `2026-Q3` with value `103.64` for the quarterly series
- **THEN** a row has `series_key` `1.10001.10.50.Q`, `time_period` `2026-Q3`, `value`
  `103.64`, `frequency` `Quarterly` and `adjustment_type` `Original`

### Requirement: Append-only raw
The fetch SHALL write one new JSON Lines file per run into `bronze_abs.s3_raw` and
never overwrite one. `bronze_abs.observations_raw` SHALL append every file with Auto
Loader, so a full refresh replays the volume without calling the ABS.

#### Scenario: Full refresh
- **WHEN** the bronze pipeline is fully refreshed
- **THEN** `observations_raw` holds the rows of every file in the volume

### Requirement: Bronze Publish and Silver Landing
`bronze_abs_publish.observations_scd2` SHALL be built by snapshot Auto CDC from the
rows of the latest fetch, without the fetch time, so a run whose values did not change
writes no row. `silver_landing.abs__observations` SHALL land its change feed, and only
changed rows SHALL get a new `transformed_timestamp`. Every column, `time_period` and
`value` included, SHALL stay as it is in Publish.

#### Scenario: A rebase
- **WHEN** a later run returns a different value for an earlier quarter, because the
  ABS moved the index to a new base period
- **THEN** Publish and Landing hold the later value and base period as the current
  version and the earlier one as a closed version, and raw keeps both

#### Scenario: First load on a new environment
- **WHEN** `run_abs` runs for the first time, so raw is empty when the update starts
- **THEN** after the run Publish holds one current version per `series_key` and
  `time_period` from that run's fetch, and Landing holds the same rows

#### Scenario: A run with no changes
- **WHEN** a run fetches the same values as the run before
- **THEN** Publish and Landing write no row and keep every `transformed_timestamp`

### Requirement: Run job and verification
Job `run_abs` SHALL run the fetch, the bronze pipeline and the silver pipeline, in that
order. With `verify=true` it SHALL also run the bronze and Silver Landing checks for
`abs`.

#### Scenario: Verified run
- **WHEN** `run_abs` runs with `verify=true`
- **THEN** the bronze checks compare raw with Publish, and the Landing checks verify
  `abs__observations`
