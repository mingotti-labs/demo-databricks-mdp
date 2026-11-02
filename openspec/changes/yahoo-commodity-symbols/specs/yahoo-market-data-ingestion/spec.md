## MODIFIED Requirements

### Requirement: Benchmarks setting
`portfolio` SHALL have a dataset `benchmarks` (`data/portfolio/benchmarks.csv`,
key `symbol`) with name, kind (`market`, `dividend`, `sector`, `volatility`,
`commodity_index`, `commodity_future`, `commodity_fund`) and sector (the GICS
sector name as Wikipedia writes it, for sector funds), loaded like the other
`portfolio` datasets.

#### Scenario: A sector fund matches its sector
- **WHEN** `benchmarks` lists `XLU` with sector `Utilities`
- **THEN** silver can compare each Utilities company with `XLU`

#### Scenario: Commodity prices are fetched
- **WHEN** `benchmarks` lists `^TRCCRB` (`commodity_index`), `GC=F`
  (`commodity_future`) and `DBC` (`commodity_fund`)
- **THEN** `run_yahoo` fetches their daily prices like any other symbol
