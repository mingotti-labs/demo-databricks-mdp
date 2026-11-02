## Why

Change 2 of the four macro-prices changes agreed on 2026-11-02 (`fred-cpi` was
change 1): daily commodity and gold prices before gold-layer work, so a 200-day
moving average and similar measures can be computed on them later. Yahoo already
fetches every symbol in the `portfolio` dataset `benchmarks` (`data/portfolio/benchmarks.csv`),
so new symbols are new rows in that file. Probes P1 and P5 (`references/poc/macro-prices/`)
found the symbols and ran them through the same steps as the fetch.

Two existing checks in `verify_silver_domain_investments.py` would fail for these
symbols: "listing has no known market" and "Yahoo exchange code has no market
mapping". Yahoo reports exchange codes for futures (`CMX`, `NYM`) and for index
providers (`FGI` for FTSE, `SNP` for S&P) that are not mapped yet. The futures trade
on NYMEX (`XNYM`); an index is not traded anywhere, and ISO 10383, the list the
`market` table is built from, has an operating market code for that: `XXXX`, "NO
MARKET (E.G. UNLISTED)". Both are already rows of `silver_domain_investments.market`.

## What Changes

- `data/portfolio/benchmarks.csv` gains 8 rows, with three new values of `kind`:
  - `commodity_index`: `^TRCCRB` (the CRB index, total return, FTSE), `^SPGSCI` (the
    S&P GSCI, weighted by world production, mostly energy).
  - `commodity_future`: `GC=F` gold, `SI=F` silver, `HG=F` copper (COMEX), `CL=F` WTI
    crude oil (NYMEX), front-month futures.
  - `commodity_fund`: `DBC` (Invesco DB Commodity Index Tracking Fund), `GSG` (iShares
    S&P GSCI Commodity-Indexed Trust).
- `YAHOO_EXCHANGE_TO_MARKET` in `src/common/investments.py` gains `CMX` and `NYM` to
  `XNYM`, and `FGI` and `SNP` to `XXXX`. Every listing keeps a market, so the checks
  stay as they are and no `listing_id` is built from an empty market.
- No change to the fetch, the pipelines or the tables: rows land in the existing
  Yahoo tables, `listing`, `price_daily` and `dividend` (DBC pays distributions).
- `data/portfolio/README.md`, the Yahoo source system file, CLAUDE.md "Sources", the
  specs `yahoo-market-data-ingestion` (kinds) and `silver-domain-investments`
  (mapping), probe P5 in the probes register.
- Not in this change: world indexes (they can reuse `FGI`/`SNP` to `XXXX` and
  add their exchanges), CPI in `market_rate_daily` (change 4).

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `yahoo-market-data-ingestion`: the benchmarks setting has three new kinds.
- `silver-domain-investments`: the exchange mapping covers futures exchanges and
  index providers (`XXXX`).

## Impact

- Tables: none new; 0 slots of the 500-table quota.
- Rows: the full price history of 8 symbols on their first fetch (probe P1: about
  55,000 price rows, back to 1984 for `^SPGSCI`), then about 8 a day.
- CI: the merge changes `data/portfolio/*.csv` and `src/common/investments.py`, which
  select `run_portfolio` and `run_investments`. `run_yahoo` is not selected (its code
  does not change), and CI runs units in alphabetical order with no dependency order,
  so prd needs two runs by hand after the merge: `run_yahoo`, then `run_investments`.
  To be confirmed with `cicd/affected_units.py` during implementation.

## Cross-repo dependencies

None.

## Model

Sonnet: CSV rows, four mapping entries, a test, documentation and the dev runs.
