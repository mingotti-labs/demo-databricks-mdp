## Context

See proposal.md. What exists and shapes this change:

- SEC is the template (`sec-company-facts`, archived): a fetch task writes dated
  JSON Lines into the source's volume, Auto Loader appends them into text raw
  tables, snapshot SCD2 is built from the latest file, bronze verification
  compares the latest file (`compare_latest_file_per`).
- Probes P6 and P6b (`references/docs/registers/probes.md`, `yfinance` 1.7.0 on
  serverless): one bulk `yf.download` of 1-year prices for 503 tickers in 54 s;
  `Ticker.dividends` for every ticker in 142 s (420 payers); options for 502 in
  36 s; `Ticker.calendar` has the next pay date for 413 of 420 payers.
- `yfinance` must be installed in the task's environment. The repo's notebook
  tasks have no environment and `%pip` is not allowed (CLAUDE.md guardrails).

## Goals / Non-Goals

**Goals:**
- Everything the shortlist reads from Yahoo, in bronze and Landing, replayable.
- One weekly fetch of about 5 minutes.

**Non-Goals:**
- Currency (S&P 500 prices are USD; the ASX change adds a currency column).
- Splitting share classes, estimating pay dates, flagging special dividends,
  any yield or growth figure (`silver_investments`).
- More than one year of prices (story decision).

## Decisions

- **D1 Fetch as a Python file task with its own environment.**
  `src/common/fetch_yahoo.py` runs as a `spark_python_task` with an
  `environment_key` whose dependencies pin `yfinance==1.7.0` (the version the
  probe proved), taking `--catalog` and `--workspace-file-path` arguments. This
  is how the probe runner ran `yfinance`. Rejected: a notebook task (no way to
  declare the dependency without `%pip`); the pipeline's own `environment`
  (the fetch is outside the pipeline, D2 of SEC).
- **D2 Helpers** in `src/common/yahoo_market.py` (symbol mapping, rows from the
  pandas results, the monthly-expiry rule, JSON Lines), unit tested without
  network; the task only calls `yfinance` and writes files.
- **D3 Re-fetch everything each run, one file per dataset per run.** Prices for
  the last year and the full dividend history are fetched every week and
  written whole. Rejected: fetching only new days. Yahoo's close is adjusted
  for splits, so a split rewrites the whole history; a full re-fetch picks that
  up and the SCD2 table records the change. Cost: about 127,000 price rows and
  35,000 dividend rows a week in raw (about 8 million rows a year), accepted
  for a demo; compression keeps it small and clustering keeps reads cheap.
  Unlike SEC, there is no write-only-when-changed: prices change every week.
- **D4 Files and columns.** `/Volumes/<catalog>/bronze_yahoo/s3_raw/<dataset>/landing/<YYYY-MM-DD>/<dataset>_<fetch time>.jsonl`.
  Every row carries `symbol` (index symbol), `yahoo_symbol` and
  `ingested_timestamp` (the task's fetch time). Columns:
  - prices: `date`, `open`, `high`, `low`, `close`, `volume`;
  - dividends: `ex_date`, `amount`;
  - calendar: `ex_dividend_date`, `dividend_date` (Yahoo's name for the pay
    date), `earnings_date`;
  - options: `has_options`, `expiry_count`, `nearest_monthly_expiry`,
    `open_interest` (calls plus puts on that expiry).
  Benchmarks have `symbol` equal to `yahoo_symbol`.
- **D5 Monthly expiry** = the first expiry on or after the fetch date that is a
  Friday between the 15th and the 21st (the third Friday), as in the probe.
  None found: `nearest_monthly_expiry` and `open_interest` empty,
  `has_options` still true if any expiry is listed.
- **D6 Tolerated gaps.** Prices missing for more than 2% of symbols fails the
  task before any file is written (Yahoo blocking or a `yfinance` break should
  stop the run, not land a partial week). Per-symbol errors in dividends,
  calendar and options are counted and logged; the task exit message reports
  every count.
- **D7 Raw tables**, as SEC: explicit all-text schema, `rescuedDataColumn`,
  `ingested_timestamp` cast to timestamp, `source_file_path`. Warn
  expectations: `symbol`, `date`, `close` (prices); `symbol`, `ex_date`,
  `amount` (dividends); `symbol` (calendar, options). `cluster_by_auto` on
  `prices_raw` and `prices_scd2`.
- **D8 Snapshot of the latest file per dataset** (`compare_latest_file_per: []`),
  bronze full pattern. Keys: prices `symbol`, `date`; dividends `symbol`,
  `ex_date`; calendar `symbol`; options `symbol`. Because the price window
  moves, each week about five days per symbol leave the window: their
  versions close. Closed versions keep older prices; silver reads current rows
  for the one-year view. Keys confirmed unique by P1 before the flows are
  written.
- **D9 Benchmarks** come from a new `portfolio` setting, `benchmark_symbols`
  (`SPY,NOBL`), not code: all curated settings live in `portfolio` (user,
  2026-10-25). `reference_rows` for `settings` goes from 5 to 6.
- **D10 Pipelines and job** as SEC: `bronze--yahoo--<target>`,
  `silver--yahoo--<target>`, job `run_yahoo` with `fetch` first. `yahoo` sorts
  after `wikipedia` and `portfolio`, so CI's alphabetical run order already
  runs its inputs first.

## Probes

- **P1 Keys and shapes** (before task 3): with the real fetch helpers on
  serverless, fetch 20 symbols (including `BRK-B`, a REIT, a non-payer and
  both benchmarks); report rows per dataset, duplicate keys, empty key values,
  the calendar's real field names and types, and the time per dataset.
- **P2 Unchanged second run**: two runs in a row in dev (task 4.2) give no new
  dividend, calendar or options versions; prices change only by the days that
  entered and left the window (plus any symbol Yahoo revised).

## Risks / Trade-offs

- [`yfinance` breaks or Yahoo blocks] → the 2% rule fails the run before a
  partial file lands; the version is pinned; P6 showed no blocking.
- [Raw grows about 8 million rows a year] → accepted (D3); a later change can
  prune old files once silver no longer needs to replay them.
- [Prices in SCD2 close every week as days leave the window] → by design (D8);
  silver uses current rows.
- [The calendar has a pay date only after a dividend is announced] → the SCD2
  versions build the history from the first load; silver estimates the rest
  (story design, `pay_date_offset_days`).

## Migration Plan

Deploy to dev; run `run_portfolio` (new setting), then `run_yahoo` with
`verify=true`; run `run_yahoo` again (P2). Stop the SQL warehouse after query
sessions. prd: CI deploys on merge and runs the affected units (portfolio,
yahoo; yahoo sorts after its inputs). Rollback: remove the resources; files
stay in the volume.
