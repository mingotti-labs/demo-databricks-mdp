## Why

`yahoo-commodity-symbols` (#143) added 8 commodity benchmarks. In dev each loaded one
year of prices, because the Yahoo fetch gives any new symbol 365 days
(`NEW_SYMBOL_DAYS`) and a reload starts from the first stored day, never earlier. The
user wants their full history in prd (the CRB from 1994, the S&P GSCI from 1984, the
futures from 2000, the funds from 2006), after which they behave like every other
Yahoo symbol.

The first plan was to seed `bronze_yahoo.fetch_state` by hand and run `run_yahoo` with
`reload_symbols`. It cannot work: the table is owned by the CI/CD service principal
and the user has only SELECT on the schema (checked 2026-11-03). Naming a new symbol in
`reload_symbols` would also lose a race with CI: the 8 symbols are in the prd
benchmarks file already, so the `run_yahoo` that CI starts after the merge of any
change to Yahoo code loads them as new symbols, for one year, before anyone can name
them.

The 500-plus S&P symbols should keep one year (full history for all of them would be
tens of millions of rows). Benchmarks are few and used as long-run references, so a
rule on them is small and declarative.

## What Changes

- `plan()` in `src/common/yahoo_market.py` takes the set of benchmark symbols. A new
  symbol (no stored prices) that is in it loads all the history Yahoo has, requested
  from 1970-01-01 (probe P6), as a full reload (all events too). Every other new
  symbol still loads one year; symbols with stored prices are unchanged.
- `fetch_yahoo.py` passes the current `portfolio` benchmarks (already read to build
  the symbol list) to `plan()`.
- Unit tests of `plan()` for the new rule.
- `verification/bronze_checks/portfolio.yml`: `benchmarks_raw` `reference_rows` 14 to
  22. #143 added 8 rows and left the pinned count behind; CI and `run_dev.py` run with
  `verify=false`, so nothing showed it. With `verify=true` the portfolio check fails
  (22 rows, more than the tolerance from 14).
- Documentation: the Yahoo source system file, CLAUDE.md "Sources", the spec
  requirement "Incremental prices and reloads", probe P6 in the probes register.
- Not in this change: dev (it keeps one year for these 8; a new dev catalog would load
  full history), loading more history for the 14 older benchmarks (`SPY`, `^VIX`, the
  sector funds: they have state, so a reload cannot go earlier than their first stored
  day), the S&P 500 symbols.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `yahoo-market-data-ingestion`: a new benchmark symbol loads its full history.

## Impact

- Tables: none new; 0 slots of the 500-table quota.
- Rows: in prd about 53,000 price rows for the 8 symbols once (probe P6: `^SPGSCI`
  10,792, `^TRCCRB` 8,174, the futures about 6,570 each, `DBC` 5,218, `GSG` 5,103)
  and the 9 `DBC` distributions, then about 8 a day.
- CI: the merge changes `yahoo_market.py` and `fetch_yahoo.py`, which select
  `run_yahoo`; `bronze_checks/portfolio.yml` selects `portfolio`. CI runs units
  alphabetically, so `run_investments` is not part of that run: after it, run
  `run_investments` by hand in prd (no dependency order, the known orchestration gap).
  To be confirmed with `cicd/affected_units.py` during implementation.
- The prd `run_yahoo` takes longer than usual once (a full-history download of 8
  symbols, about a minute each).

## Cross-repo dependencies

None.

## Model

Sonnet: one rule in a helper with tests, a pinned count, documentation, and the dev
check.
