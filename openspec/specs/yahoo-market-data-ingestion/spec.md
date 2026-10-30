# yahoo-market-data-ingestion Specification

## Purpose
Yahoo Finance prices, dividend and split events, next pay dates and options
activity for the dividend portfolio story, fetched incrementally into
append-only, replayable raw files and tables, with Bronze Publish and Silver
Landing.

## Requirements

### Requirement: Symbols to fetch
Each run SHALL fetch every symbol ever seen in the S&P 500 list
(`bronze_wikipedia_publish.sp500_constituents_scd2`, current and closed
versions), written the way Yahoo writes it (a dot becomes a dash, `BRK.B` is
`BRK-B`), plus every symbol in the current `portfolio` dataset `benchmarks`.
Each row SHALL keep both the index symbol and the Yahoo symbol.

#### Scenario: A dotted symbol is fetched
- **WHEN** the S&P 500 list holds `BRK.B`
- **THEN** Yahoo is asked for `BRK-B` and its rows carry `symbol` `BRK.B` and
  `yahoo_symbol` `BRK-B`

#### Scenario: A former member is still fetched
- **WHEN** a symbol's S&P 500 version was closed (it left the index)
- **THEN** its prices are still fetched

#### Scenario: Benchmarks are fetched
- **WHEN** `benchmarks` lists `SPY` and `^VIX`
- **THEN** prices for both are fetched, with `symbol` equal to `yahoo_symbol`

### Requirement: Datasets
Each run SHALL fetch, values kept as Yahoo returned them:
- prices: daily open, high, low, close, adjusted close and volume;
- events: dividends (ex-date, amount) and splits (date, ratio);
- calendar: the next announced ex-date and pay date, where Yahoo has one;
- options: whether options are listed, the nearest monthly expiry and its
  total open interest and total volume.

#### Scenario: A company that pays no dividend
- **WHEN** a symbol has no dividend history
- **THEN** it has no dividend events and the run does not fail

### Requirement: Incremental prices and reloads
For a symbol already fetched, prices SHALL be fetched from its last stored
price date minus one day, and those days overwritten. A symbol SHALL be
reloaded in full (prices from its first stored date, or one year for a new
symbol, and all its events) when it has no stored prices, when a dividend or
split falls in the newly fetched days, or when the job parameter
`reload_symbols` names it (`*` reloads every symbol).

#### Scenario: A day stored while the market was open
- **WHEN** the last stored day was fetched before that day's close
- **THEN** the next run fetches that day again and overwrites it

#### Scenario: A dividend triggers a reload
- **WHEN** a symbol goes ex-dividend in the newly fetched days
- **THEN** its prices, including every earlier adjusted close, and its events
  are fetched again in full

#### Scenario: A split triggers a reload
- **WHEN** a symbol splits in the newly fetched days
- **THEN** its prices and its events, which Yahoo restates for the split, are
  fetched again in full

#### Scenario: A manual reload
- **WHEN** the job runs with `reload_symbols` `AAPL`
- **THEN** AAPL is reloaded in full and the other symbols are fetched as usual

### Requirement: Fetch state and resuming
The fetch SHALL keep one row per symbol in `bronze_yahoo.fetch_state`: Yahoo
symbol, first and last stored price date, the job run id and time of its last
fetch, and its last outcome. The fetch SHALL work in batches of symbols and
update the state only after that batch's files are written. A repaired run
(same job run id) SHALL skip symbols the run already fetched.

#### Scenario: A repaired run resumes
- **WHEN** a run fails after half the batches and is repaired
- **THEN** the repair fetches only the symbols that run had not yet fetched

### Requirement: Tolerated gaps
The run SHALL fail, after writing its files, when more than 2% of the current
S&P 500 members return no prices. Former members and benchmarks with no
prices SHALL be logged and never fail the run. Missing events, calendar or
options for a symbol SHALL never fail the run.

#### Scenario: One member has no prices
- **WHEN** one of about 503 current members returns no prices
- **THEN** the run succeeds and logs that symbol

#### Scenario: An acquired company returns nothing
- **WHEN** a former member no longer trades
- **THEN** the run logs it and does not count it against the 2%

### Requirement: Append-only raw files and tables
Each batch SHALL write one new dated JSON Lines file per dataset under
`/Volumes/<catalog>/bronze_yahoo/s3_raw/<dataset>/landing/`, never overwriting
or deleting an earlier file, with `ingested_timestamp` set by the fetch.
`bronze_yahoo.<dataset>_raw` SHALL be streaming tables that append every new
file's rows, with warn expectations on required fields; `prices_raw` SHALL use
automatic liquid clustering.

#### Scenario: Raw keeps every fetch
- **WHEN** the job has run twice
- **THEN** each raw table holds the rows of both runs

### Requirement: Bronze Publish
`bronze_yahoo_publish` SHALL hold `prices_scd1` (key `symbol`, `date`),
`events_scd1` (key `symbol`, `date`, `event_type`), `options_scd1` (key
`symbol`) and `calendar_scd2` (key `symbol`), each built by streaming Auto CDC
from its raw table sequenced by `ingested_timestamp`, with change data feed on.

#### Scenario: A reload restates prices
- **WHEN** a symbol is reloaded after a dividend
- **THEN** `prices_scd1` holds the new adjusted close for every stored day

#### Scenario: A new pay date is announced
- **WHEN** a symbol's next pay date changes between two runs
- **THEN** its calendar version is closed and a new one inserted, so the
  history of announced pay dates is kept

### Requirement: Benchmarks setting
`portfolio` SHALL have a dataset `benchmarks` (`data/portfolio/benchmarks.csv`,
key `symbol`) with name, kind (`market`, `dividend`, `sector`, `volatility`)
and sector (the GICS sector name as Wikipedia writes it, for sector funds),
loaded like the other `portfolio` datasets.

#### Scenario: A sector fund matches its sector
- **WHEN** `benchmarks` lists `XLU` with sector `Utilities`
- **THEN** silver can compare each Utilities company with `XLU`

### Requirement: Silver Landing
`silver_landing.yahoo__<dataset>` SHALL be built from each Bronze Publish change
feed with `land_changes`, keyed by the same natural keys.

#### Scenario: Landing matches Bronze Publish
- **WHEN** the silver pipeline has run
- **THEN** each Landing table's current rows equal its Bronze Publish table's
  current rows

### Requirement: Run job and verification
Job `run_yahoo` SHALL run the fetch, the bronze pipeline, then (with
`verify=true`) bronze verification, the silver pipeline, Silver Landing
verification, and the design pattern tags.

#### Scenario: Verified run passes
- **WHEN** `run_yahoo` is run with `verify=true` in dev
- **THEN** every task succeeds
