## Why

Step 5 of the dividend portfolio story (`demo-databricks-planning`, story design
revised 2026-10-25). The shortlist needs each company's yield, dividend history
and growth, price and total return, whether options trade, and the next pay
date, compared with benchmark funds. Yahoo Finance (`yfinance`) gives all of it
free for the whole index (probes P6 and P6b: 503 tickers from serverless, no
blocking). Second source on the append-only, replayable raw pattern built for
SEC (`bronze_volume_append_autoloader_python`).

## What Changes

- New source `yahoo`, run weekly by job `run_yahoo`:
  - A **fetch notebook** (the only one allowed `%pip install`, pinning
    `yfinance`) fetches every symbol ever seen in the S&P 500 list
    (`bronze_wikipedia_publish`, dots turned into Yahoo's dashes) plus the
    benchmarks from `portfolio`, in batches, and writes one dated JSON Lines
    file per dataset per batch into `bronze_yahoo.s3_raw`:
    - `prices`: daily open, high, low, close, adjusted close and volume;
    - `events`: dividends and splits;
    - `calendar`: the next announced ex-date and pay date per symbol;
    - `options`: whether options are listed and the activity on the nearest
      monthly expiry.
  - **Incremental prices**: each run fetches from the last stored date minus
    one day. A symbol with a dividend or split in the new days, a new symbol,
    or one named in the job parameter `reload_symbols` is reloaded in full.
  - **Fetch state**: table `bronze_yahoo.fetch_state`, one row per symbol,
    written by the fetch notebook; it holds the stored date range and the run
    that last fetched the symbol, so a repaired run carries on from where it
    stopped.
  - **Bronze raw**: four append-only Auto Loader streaming tables
    `bronze_yahoo.<dataset>_raw`.
  - **Bronze Publish**: `prices`, `events` and `options` as SCD1, `calendar` as
    SCD2 (the history of announced pay dates), all streaming Auto CDC from raw.
  - **Silver Landing**: four tables in `silver_landing_yahoo` via `land_changes`.
- `portfolio` gains a dataset `benchmarks` (`data/portfolio/benchmarks.csv`):
  SPY, NOBL, `^VIX` and the 11 SPDR sector funds, with kind and sector.
- CLAUDE.md guardrails: an exception allowing `%pip install` in the Yahoo
  fetch notebook only.
- Not in this change: currency (all S&P 500 prices are USD; the ASX change
  adds it), choosing between share classes, the index-membership flag (the
  company dimension in `silver_investments`), the pay-date estimate and any
  calculation.

## Capabilities

### New Capabilities
- `yahoo-market-data-ingestion`: fetch Yahoo prices, events, calendar and
  options activity incrementally into append-only raw files and tables,
  Bronze Publish and Silver Landing.

### Modified Capabilities

## Impact

- New: `src/common/yahoo_market.py` (helpers, unit tests),
  `src/common/fetch_yahoo.py` (notebook), `src/layers/bronze/yahoo/`,
  `src/layers/bronze/yahoo_publish/`, `src/layers/silver/landing/yahoo/`, two
  pipelines, job `run_yahoo`, verification entries.
- `portfolio`: `benchmarks` added to its raw, SCD2 and Landing tables.
- Volume `bronze_yahoo.s3_raw` exists (iac `raw-volumes-sec-yahoo-wikipedia`).
- Tables: 13 new per target for yahoo (4 raw, 4 Publish, 4 Landing, fetch
  state) and 3 for `portfolio.benchmarks`.
- Raw growth: about 2,500 new price rows a week plus about 10,000 from reloads
  (symbols that went ex-dividend that week).
- External: `yfinance` is unofficial and may break or rate-limit.

## Cross-repo dependencies

None new: uses `bronze_yahoo.s3_raw` from `raw-volumes-sec-yahoo-wikipedia`
in `demo-databricks-iac` (applied).

## Model

Opus: a new external dependency, an incremental fetch with its own state, and
a reload rule driven by corporate events.
