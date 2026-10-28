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
    date), `earnings_date` (Yahoo sends a list; the first date is kept). The
    earnings and revenue estimates Yahoo also sends are not needed and not kept;
  - options: `has_options`, `expiry_count`, `nearest_monthly_expiry`,
    `open_interest` and `volume` (calls plus puts on that expiry, both as
    sent). P1 found open interest 0 on every strike, even for AAPL, while
    volume is filled in, so `volume` is the activity measure until Yahoo's
    open interest comes back; silver decides which to use.
  Benchmarks have `symbol` equal to `yahoo_symbol`.
- **D5 Monthly expiry** = the first expiry on or after the fetch date that is a
  Friday between the 15th and the 21st (the third Friday), as in the probe.
  None found: `nearest_monthly_expiry`, `open_interest` and `volume` empty,
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
  **Result (2026-10-28, `references/poc/dividend-portfolio/p8_yahoo_shapes.py`):**
  prices 251 trading days per symbol, 5,020 rows, `symbol, date` unique, no
  empty key, columns Open, High, Low, Close, Adj Close, Volume (Close equals
  Adj Close on these days; raw Close is what we keep); dividends 2,632 rows for
  17 payers, `symbol, ex_date` unique (BRK-B, AMZN and TSLA pay none), the
  ex-date carries a New York time of 09:30, so the date part in New York time
  is the ex-date; calendar fields `Dividend Date` (pay date) and
  `Ex-Dividend Date` (dates), `Earnings Date` (a list), plus estimates; ETFs
  return an empty calendar; options listed for all 20 symbols, but open
  interest is 0 on every AAPL strike (monthly and nearest expiry) while volume
  is filled in (about 35,000 contracts on the November monthly), hence D4's
  `volume`. Times for 20 symbols: prices 2.8 s, dividends 6.6 s, calendar
  2.1 s, options 3.3 s (about 2, 2.7, 0.9 and 1.4 minutes for 505).
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
