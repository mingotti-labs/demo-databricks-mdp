## MODIFIED Requirements

### Requirement: Incremental prices and reloads
For a symbol already fetched, prices SHALL be fetched from its last stored
price date minus one day, and those days overwritten. A symbol SHALL be
reloaded in full (prices from its first stored date, or for a new symbol one
year, or all the history Yahoo has when the new symbol is in `portfolio`
`benchmarks`, and all its events) when it has no stored prices, when a dividend
or split falls in the newly fetched days, or when the job parameter
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

#### Scenario: A new index member
- **WHEN** a symbol with no stored prices is not in `benchmarks`
- **THEN** the run loads its last year of prices and all its events

#### Scenario: A new benchmark
- **WHEN** a symbol with no stored prices is in `benchmarks`, for example `^TRCCRB`
- **THEN** the run requests prices from 1970-01-01, stores every day Yahoo has from
  the symbol's first trading day, and all its events; later runs are incremental
