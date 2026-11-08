# fred-rates-ingestion Specification

## Purpose
TBD - created by archiving change fred-rates. Update Purpose after archive.

## Requirements

### Requirement: Series fetched
Each run SHALL fetch every series named in `src/common/fred_series.py`
(`DGS10`, the US 10-year Treasury yield; `DGS3MO`, `DGS1`, `DGS2` and `DGS3`, the US 3-month, 1-year, 2-year and
3-year Treasury yields; `DFF`, the effective federal funds
rate; `DFEDTARU` and `DFEDTARL`, the upper and lower limit of the federal funds
target range; `CPIAUCSL`, `CPIAUCNS` and `CPILFESL`, the US consumer price index
for all urban consumers: all items seasonally adjusted, all items not seasonally
adjusted, and all items less food and energy seasonally adjusted; the Nominal Broad U.S. Dollar Index `DTWEXBGS`; the daily exchange rates `DEXUSEU`,
`DEXJPUS`, `DEXUSUK`, `DEXSZUS`, `DEXCAUS`, `DEXSDUS`, `DEXUSAL`, `DEXUSNZ` and `DEXCHUS`; the ECB deposit
facility rate `ECBDFR`; the OECD short-term rates `IRSTCI01GBM156N`, `IR3TIB01JPM156N`, `IR3TIB01CAM156N`,
`IR3TIB01CHM156N`, `IR3TIB01SEM156N`, `IR3TIB01NZM156N`, `IR3TIB01CNM156N`; and the OECD long-term rates
`IRLTLT01EZM156N`, `IRLTLT01JPM156N`, `IRLTLT01GBM156N`, `IRLTLT01CHM156N`, `IRLTLT01CAM156N`, `IRLTLT01SEM156N`,
`IRLTLT01NZM156N`) from the FRED
API at the address in the bundle variable `fred_api_url`, using the key in secret
`api_key` of scope `fred`. For each it SHALL read the series' title, units and
frequency and its observations.

#### Scenario: The 10-year yield is fetched
- **WHEN** `run_fred` runs
- **THEN** rows exist for `series_id` `DGS10` with `title` "Market Yield on U.S.
  Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment
  Basis", `units` `Percent` and `frequency` `Daily`

#### Scenario: The short-term US yields are fetched
- **WHEN** `run_fred` runs for the first time after `DGS3MO`, `DGS1`, `DGS2` and `DGS3` are added
- **THEN** rows exist for each with `frequency` `Daily`, `DGS3MO` from 1981-09-01, `DGS2` from 1976-06-01 and `DGS1` and
  `DGS3` from 1962-01-02

#### Scenario: The Fed's policy rate is fetched
- **WHEN** `run_fred` runs
- **THEN** rows exist for `series_id` `DFEDTARU` and `DFEDTARL` (daily since
  2008-12-16) and `DFF`, each with its own `title`

#### Scenario: Consumer prices are fetched
- **WHEN** `run_fred` runs
- **THEN** rows exist for `series_id` `CPIAUCSL` (since 1947-01-01), `CPIAUCNS`
  (since 1913-01-01) and `CPILFESL` (since 1957-01-01), each with `frequency`
  `Monthly` and every `observation_date` on the first day of a month

#### Scenario: A series is added to the list
- **WHEN** a series named in `fred_series.py` has no stored rows
- **THEN** the run requests all its observations, and the other series stay
  incremental

#### Scenario: A request fails
- **WHEN** FRED answers a request with an error status
- **THEN** the fetch task fails with the status and FRED's message, writes no
  file for that run, and neither the key nor a URL containing it is logged

#### Scenario: A new series loads its whole history
- **WHEN** `run_fred` runs for the first time after `DEXSZUS` is added
- **THEN** rows exist for `DEXSZUS` from 1971-01-04

### Requirement: Observation rows
Each row SHALL hold `series_id`, `observation_date` (`yyyy-MM-dd`), `value`
as FRED sent it, `title`, `units`, `frequency` and `ingested_timestamp`, the
fetch time. Observations whose value is `.` SHALL be skipped. FRED's
`realtime_start` and `realtime_end` SHALL NOT be kept.

#### Scenario: A holiday
- **WHEN** FRED returns `1962-02-12` with the value `.`
- **THEN** no row is written for that date

#### Scenario: A yield on a day
- **WHEN** FRED returns `2026-10-29` with the value `4.98`
- **THEN** a row has `observation_date` `2026-10-29` and `value` `4.98`

### Requirement: Incremental request and reload
For a series with stored rows, the fetch SHALL request observations from 31 days
before the series' last stored `observation_date`. With no stored rows, or when
the job parameter `reload` is `true`, it SHALL request all observations.

#### Scenario: Weekly run
- **WHEN** the last stored date is `2026-10-29`
- **THEN** the request asks for observations from `2026-09-28`

#### Scenario: Reload
- **WHEN** `run_fred` runs with `reload=true`
- **THEN** every observation of every series is requested

### Requirement: Append-only raw
The fetch SHALL write one new JSON Lines file per run into `bronze_fred.s3_raw`
and never overwrite one. `bronze_fred.observations_raw` SHALL append every file
with Auto Loader, so a full refresh replays the volume without calling FRED.

#### Scenario: Full refresh
- **WHEN** the bronze pipeline is fully refreshed
- **THEN** `observations_raw` holds the rows of every file in the volume

### Requirement: Bronze Publish and Silver Landing
`bronze_fred_publish.observations_scd1` SHALL hold one row per `series_id` and
`observation_date`, the value from the latest `ingested_timestamp` (SCD1).
`silver_landing.fred__observations` SHALL land its change feed with
`observation_date` as a date; every other column, `value` included, stays as in
Publish. A value that does not read as a date SHALL fail the update.

#### Scenario: Dates in Landing
- **WHEN** Publish holds `observation_date` `2026-10-29`
- **THEN** Landing holds the date 2026-10-29, as type DATE

#### Scenario: A revised value
- **WHEN** a later run writes a different value for `DGS10` on a date
- **THEN** Publish and Landing hold the later value, and raw keeps both

### Requirement: Run job and verification
Job `run_fred` SHALL run the fetch, the bronze pipeline and the silver
pipeline, and with `verify=true` the bronze and Silver Landing checks. CI SHALL
run it after a deploy that affects it.

#### Scenario: Verified run
- **WHEN** `run_fred` runs with `verify=true`
- **THEN** the checks find no null keys and no duplicate `series_id` and
  `observation_date` in Publish, Publish equal to the latest raw row per key,
  and Landing rows equal to Publish
