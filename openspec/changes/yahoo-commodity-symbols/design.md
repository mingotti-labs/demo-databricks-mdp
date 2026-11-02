## Context

See proposal.md. Probes, 2026-11-02 and 2026-11-03, scripts and results in
`references/poc/macro-prices/`:

- P1: daily history per symbol and Yahoo's exchange code. `^CRB` and `^BCOM` do not
  exist on Yahoo; the CRB is `^TRCCRB`.

| Symbol | What | From | Exchange | Market |
|---|---|---|---|---|
| `^TRCCRB` | CRB index, total return | 1994-01-03 | `FGI` | `XXXX` (new) |
| `^SPGSCI` | S&P GSCI index | 1984-01-03 | `SNP` | `XXXX` (new) |
| `GC=F` | gold, COMEX front month | 2000-08-30 | `CMX` | `XNYM` (new) |
| `SI=F` | silver, COMEX front month | 2000-08-30 | `CMX` | `XNYM` (new) |
| `HG=F` | copper, COMEX front month | 2000-08-30 | `CMX` | `XNYM` (new) |
| `CL=F` | WTI crude oil, NYMEX front month | 2000-08-23 | `NYM` | `XNYM` (new) |
| `DBC` | Invesco DB Commodity Index Tracking Fund | 2006-02-06 | `PCX` | `XNYS` |
| `GSG` | iShares S&P GSCI Commodity-Indexed Trust | 2006-07-21 | `PCX` | `XNYS` |

- P5: the 8 symbols through the fetch's own steps (one `yf.download`, then actions,
  calendar, options, rows built with `common.yahoo_market`): all 8 return prices and
  a calendar row with their exchange code; none fails. Yahoo prints "No fundamentals
  data found" for the calendar call and returns an empty calendar, as for `^VIX`.
  Only the two funds have options; `DBC` has 9 events (distributions).
- `silver_domain_investments.market` (dev, 2026-11-03) has `XNYM` (NEW YORK
  MERCANTILE EXCHANGE, CME Group) and `XXXX` (NO MARKET (E.G. UNLISTED), country
  `ZZ`), both active.

## Goals / Non-Goals

**Goals:**
- Daily prices for the CRB, the S&P GSCI, gold, silver, copper, crude oil and two
  commodity funds, in `price_daily`, through the existing benchmarks path.
- Every listing keeps a known market.

**Non-Goals:**
- Continuous futures adjustment (rolls), spot gold (LBMA, licensed), other
  currencies; world indexes; CPI.

## Decisions

**D1. New benchmarks rows, not a new source.** The Yahoo fetch already takes every
symbol in `benchmarks`; the CSV is the master and `run_portfolio` copies it.

**D2. Indexes map to ISO `XXXX`.** `FGI` and `SNP` are Yahoo's codes for FTSE and
S&P indexes; none is traded on a market. ISO 10383's own "no market" code keeps the
`market` table a copy of the standard (no row invented here), keeps both verification
checks unchanged, and gives a stable `listing_id` (an empty market would be left out
of the hash and change the id once filled). Rejected: an empty `market_code` with
exceptions in the checks; a home-made "N/A" market row (the unknown-member row
belongs in gold dimensions); mapping `FGI`/`SNP` to the exchanges where CRB and
GSCI futures trade (it would also place `^GSPC` on the CME later). `XOFF`
(off-exchange trades in listed instruments) does not describe an index.

**D3. Futures map to the operating market `XNYM`.** COMEX (`XCEC`) is a segment of
NYMEX in ISO 10383; `market` holds operating markets only, as for every other code
in the mapping.

**D4. Kinds name what the row is.** `commodity_index`, `commodity_future` and
`commodity_fund` sit next to `market`, `dividend`, `sector` and `volatility`, so gold
can pick a measure (index) or a holding (fund).

## Risks / Trade-offs

- [Front-month futures jump on the roll to the next contract] -> they are a price
  level for gold and oil, not a return series; the funds and indexes carry the roll.
- [CI does not run `run_yahoo`, and runs `run_investments` before `run_portfolio`]
  -> two hand runs in prd after the merge (tasks); the dependency-order idea stays
  on the backlog (orchestration change).
- [`yfinance` is unofficial and a symbol can vanish] -> as today: a benchmark with no
  prices is reported as "others missing" and does not fail the run.
