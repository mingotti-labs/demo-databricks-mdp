## ADDED Requirements

### Requirement: Tables fetched
Each run SHALL download RBA tables F11.1 (`f11.1-data.csv`, exchange rates),
F1 (`f1-data.csv`, money market rates including the cash rate target), F2
(`f2-data.csv`, government bond yields) and F5 (`f5-data.csv`, indicator
lending rates) from the address in the bundle variable `rba_tables_url`,
sending the `http_user_agent` string.

#### Scenario: All files are fetched
- **WHEN** `run_rba` runs
- **THEN** the four files are downloaded and the run writes rows for table ids
  `F11.1`, `F1`, `F2` and `F5`

#### Scenario: A file cannot be read
- **WHEN** a file has no `Series ID` header row or the download fails
- **THEN** the fetch task fails and writes no file for that run

### Requirement: Observation rows
The fetch SHALL turn each file into one row per series and date with a value,
skipping empty cells. Each row SHALL hold `table_id`, `series_id`,
`observation_date` and `value` as the RBA wrote them, the series' `title`,
`description`, `frequency`, `type`, `units`, `source` and `publication_date`
from the header rows, and `ingested_timestamp`, the fetch time.

#### Scenario: AUD/USD on a day
- **WHEN** F11.1 has `03-Jan-2023` with `0.6828` under series `FXRUSD`
- **THEN** a row has `table_id` `F11.1`, `series_id` `FXRUSD`,
  `observation_date` `03-Jan-2023`, `value` `0.6828` and `units` `USD`

#### Scenario: A bond yield and a housing rate
- **WHEN** F2 has a value for `FCMYGBAG10D` and F5 for `FILRHLBVS`
- **THEN** rows exist with those `series_id`s, `table_id` `F2` and `F5`, and
  `units` `Per cent per annum`

#### Scenario: An empty cell
- **WHEN** F1's latest date has no value for `FIRMMCRTD`
- **THEN** no row is written for that series and date

### Requirement: Incremental write and reload
For a table with stored rows, the fetch SHALL write only rows dated from 31
days before that table's last stored `observation_date`. With no stored rows,
or when the job parameter `reload` is `true`, it SHALL write every row.

#### Scenario: Weekly run
- **WHEN** F11.1's last stored date is `23-Oct-2026`
- **THEN** the run writes F11.1 rows dated `22-Sep-2026` or later

#### Scenario: Reload
- **WHEN** `run_rba` runs with `reload=true`
- **THEN** every row of both files is written

### Requirement: Append-only raw
The fetch SHALL write one new JSON Lines file per table per run into
`bronze_rba.s3_raw` and never overwrite one. `bronze_rba.observations_raw`
SHALL append every file with Auto Loader, so a full refresh replays the volume
without calling the RBA.

#### Scenario: Full refresh
- **WHEN** the bronze pipeline is fully refreshed
- **THEN** `observations_raw` holds the rows of every file in the volume

### Requirement: Bronze Publish and Silver Landing
`bronze_rba_publish.observations_scd1` SHALL hold one row per `series_id` and
`observation_date`, the value from the latest `ingested_timestamp` (SCD1).
`silver_landing.rba__observations` SHALL land its change feed with
`observation_date` and `publication_date` as dates (read from `dd-Mon-yyyy`);
every other column, `value` included, stays as in Publish. A value that does
not read as a date SHALL fail the update instead of becoming null.

#### Scenario: Dates in Landing
- **WHEN** Publish holds `observation_date` `03-Jan-2023` and `publication_date`
  `30-Oct-2026`
- **THEN** Landing holds the dates 2023-01-03 and 2026-10-30, as type DATE

#### Scenario: A revised value
- **WHEN** a later run writes a different value for `FXRUSD` on a date
- **THEN** Publish and Landing hold the later value, and raw keeps both

### Requirement: Run job and verification
Job `run_rba` SHALL run the fetch, the bronze pipeline and the silver
pipeline, and with `verify=true` the bronze and Silver Landing checks. CI
SHALL run it after a deploy that affects it.

#### Scenario: Verified run
- **WHEN** `run_rba` runs with `verify=true`
- **THEN** the checks find no null keys and no duplicate `series_id` and
  `observation_date` in Publish, Publish equal to the latest raw row per key,
  and Landing rows equal to Publish
