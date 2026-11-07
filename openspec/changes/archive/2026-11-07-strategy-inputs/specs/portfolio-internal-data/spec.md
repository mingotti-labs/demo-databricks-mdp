## ADDED Requirements

### Requirement: Bear funds in the benchmarks
`data/portfolio/benchmarks.csv` SHALL list the bear funds of strategy 001 with kind `bear_fund`: SQQQ, PSQ, SH, SDS and
SPXU, so the Yahoo source loads their full price history like every benchmark.

#### Scenario: A bear fund has prices
- **WHEN** `run_yahoo` and `run_investments` have run after the rows were added
- **THEN** `price_daily` has SQQQ from 2010 and SH from 2006 up to the latest trading day
