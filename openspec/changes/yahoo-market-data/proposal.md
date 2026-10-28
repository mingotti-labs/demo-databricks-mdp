## Why

Step 5 of the dividend portfolio story (`demo-databricks-planning`, story design
revised 2026-10-25). The shortlist needs each company's yield, dividend history
and growth, price return, whether options trade, and the next pay date. Yahoo
Finance (`yfinance`) gives all of it free for the whole index (probes P6 and
P6b: 503 tickers from serverless, no blocking). Second source on the
append-only, replayable raw pattern built for SEC
(`bronze_volume_append_autoloader_python`).

## What Changes

- New source `yahoo`, run weekly by job `run_yahoo`:
  - A **fetch task** reads the current S&P 500 symbols (`bronze_wikipedia_publish`,
    dots turned into Yahoo's dashes) plus the benchmark symbols from the
    `portfolio` settings, and writes one dated JSON Lines file per dataset per
    run into `bronze_yahoo.s3_raw`:
    - `prices`: one year of daily raw prices (open, high, low, close, volume),
      not Yahoo's dividend-adjusted series;
    - `dividends`: the full dividend history per symbol (ex-date, amount);
    - `calendar`: the next announced ex-date and pay date per symbol;
    - `options`: whether options are listed and the open interest on the
      nearest monthly expiry.
  - **Bronze raw**: four append-only Auto Loader streaming tables
    `bronze_yahoo.<dataset>_raw`, text values, warn expectations,
    `cluster_by_auto` on prices.
  - **Bronze Publish**: four SCD2 tables in `bronze_yahoo_publish` from the
    latest file (bronze full pattern), so the weekly calendar versions become
    the history of announced pay dates.
  - **Silver Landing**: four tables in `silver_landing_yahoo` via `land_changes`.
- `portfolio` settings gain one row: `benchmark_symbols` = `SPY,NOBL`.
- Not in this change: currency (all S&P 500 prices are USD; the ASX change
  adds it), choosing between share classes, the pay-date estimate and any
  calculation (the `silver_investments` change).

## Capabilities

### New Capabilities
- `yahoo-market-data-ingestion`: fetch Yahoo prices, dividends, calendar and
  options activity into append-only raw files and tables, SCD2 history and
  Silver Landing.

### Modified Capabilities

## Impact

- New: `src/common/yahoo_market.py` (helpers, unit tests),
  `src/common/fetch_yahoo.py` (Python file task with a pinned `yfinance`),
  `src/layers/bronze/yahoo/`, `src/layers/bronze/yahoo_publish/`,
  `src/layers/silver/landing/yahoo/`, two pipelines, job `run_yahoo`,
  verification entries.
- Volume `bronze_yahoo.s3_raw` exists (iac `raw-volumes-sec-yahoo-wikipedia`).
- Tables: 12 new per target (4 raw, 4 SCD2, 4 Landing).
- Raw growth: about 127,000 price rows and 35,000 dividend rows a week (the
  whole year and the whole history are re-fetched; see design D3).
- External: `yfinance` is unofficial and may break or rate-limit; the probe
  fetched everything in about 4 minutes.

## Cross-repo dependencies

None new: uses `bronze_yahoo.s3_raw` from `raw-volumes-sec-yahoo-wikipedia`
in `demo-databricks-iac` (applied).

## Model

Opus: a new external dependency and a time series on a snapshot pattern, with
two probes before the code settles.
