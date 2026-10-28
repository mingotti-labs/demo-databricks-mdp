## Purpose

Yahoo Finance prices, dividends, next pay dates and options activity for the
dividend portfolio story, fetched into append-only, replayable raw files and
tables, with SCD2 history and Silver Landing.

## ADDED Requirements

### Requirement: Symbols to fetch
Each run SHALL fetch every symbol currently in the S&P 500 list
(`bronze_wikipedia_publish`), written the way Yahoo writes it (a dot becomes a
dash, `BRK.B` is `BRK-B`), plus the benchmark symbols in the current
`portfolio` setting `benchmark_symbols`. Each row SHALL keep both the index
symbol and the Yahoo symbol.

#### Scenario: A dotted symbol is fetched
- **WHEN** the S&P 500 list holds `BRK.B`
- **THEN** Yahoo is asked for `BRK-B` and its rows carry `symbol` `BRK.B` and
  `yahoo_symbol` `BRK-B`

#### Scenario: Benchmarks are fetched
- **WHEN** `benchmark_symbols` is `SPY,NOBL`
- **THEN** prices for `SPY` and `NOBL` are fetched with the index symbols

### Requirement: Datasets
Each run SHALL fetch, values kept as Yahoo returned them:
- prices: one year of daily open, high, low, close and volume, not adjusted for
  dividends;
- dividends: the full dividend history (ex-date, amount);
- calendar: the next announced ex-date and pay date, where Yahoo has one;
- options: whether options are listed, the nearest monthly expiry and its
  total open interest and total volume.

#### Scenario: A company that pays no dividend
- **WHEN** a symbol has no dividend history
- **THEN** it has no dividend rows and the run does not fail

### Requirement: Tolerated gaps
The run SHALL fail when more than 2% of the symbols return no prices; fewer
missing symbols SHALL be logged and skipped. Missing dividends, calendar or
options for a symbol SHALL never fail the run.

#### Scenario: One symbol has no prices
- **WHEN** one of about 505 symbols returns no prices
- **THEN** the run succeeds and logs that symbol

### Requirement: Append-only raw files and tables
Each run SHALL write one new dated JSON Lines file per dataset under
`/Volumes/<catalog>/bronze_yahoo/s3_raw/<dataset>/landing/`, never overwriting
or deleting an earlier file, with `ingested_timestamp` set by the fetch task.
`bronze_yahoo.<dataset>_raw` SHALL be streaming tables that append every new
file's rows, with warn expectations on required fields; `prices_raw` SHALL use
automatic liquid clustering.

#### Scenario: Raw keeps every fetch
- **WHEN** the job has run twice
- **THEN** each raw table holds the rows of both runs

### Requirement: Bronze Publish SCD2
`bronze_yahoo_publish.<dataset>_scd2` SHALL be built from each dataset's latest
file by snapshot Auto CDC on its natural key (prices `symbol`, `date`;
dividends `symbol`, `ex_date`; calendar and options `symbol`), following the
bronze full pattern.

#### Scenario: A new pay date is announced
- **WHEN** a symbol's next pay date changes between two runs
- **THEN** its calendar version is closed and a new one inserted, so the
  history of announced pay dates is kept

#### Scenario: An unchanged dividend history writes no version
- **WHEN** a symbol's dividends are the same in two runs
- **THEN** its dividend rows get no new or closed version

### Requirement: Silver Landing
`silver_landing_yahoo.<dataset>` SHALL be built from each SCD2 change feed with
`land_changes`, keyed by the same natural keys.

#### Scenario: Landing matches Bronze Publish
- **WHEN** the silver pipeline has run
- **THEN** each Landing table's current rows equal its SCD2 table's current rows

### Requirement: Run job and verification
Job `run_yahoo` SHALL run the fetch, the bronze pipeline, then (with
`verify=true`) bronze verification, the silver pipeline, Silver Landing
verification, and the design pattern tags.

#### Scenario: Verified run passes
- **WHEN** `run_yahoo` is run with `verify=true` in dev
- **THEN** every task succeeds
