## Context

See proposal.md. What exists and shapes this change:

- SEC is the template for raw (`sec-company-facts`, archived): a fetch task
  writes dated JSON Lines into the source's volume, Auto Loader appends them
  into text raw tables (`bronze_volume_append_autoloader_python`).
- Streaming Auto CDC from an append-only raw table is a registered pattern
  (`bronze_publish_scd1_autocdc_stream_python`, clickstream); `land_changes`
  already handles SCD1 (`scd2=False`) and SCD2 sources.
- Probes P6 and P6b (`references/docs/registers/probes.md`, `yfinance` 1.7.0 on
  serverless): one bulk `yf.download` of 1-year prices for 503 tickers in 54 s;
  `Ticker.dividends` for every ticker in 142 s (420 payers); options for 502 in
  36 s; `Ticker.calendar` has the next pay date for 413 of 420 payers.
- How Yahoo restates history (checked locally on NVDA's 10-for-1 split of
  2024-06-10, `yfinance` 1.7.0): `Close` is split-adjusted (2024-06-07 shows
  120.89, the real close was about 1,208); `Ticker.dividends` is split-adjusted
  (the March 2024 dividend of 0.04 shows 0.004); `Adj Close` is also adjusted
  for every later dividend; `history(actions=True)` returns `Dividends` and
  `Stock Splits` columns per day.

## Goals / Non-Goals

**Goals:**
- Everything the shortlist reads from Yahoo, in bronze and Landing, replayable.
- An incremental weekly fetch that resumes after a failure and reloads a
  symbol whenever Yahoo restates its history.

**Non-Goals:**
- Currency (S&P 500 prices are USD; the ASX change adds a currency column).
- The index-membership flag, share classes, the pay-date estimate, special
  dividends, any yield or growth figure (`silver_investments`).
- Members before our first Wikipedia load (not in our history).

## Decisions

- **D1 Fetch notebook with `%pip`** (user, 2026-10-29).
  `src/common/fetch_yahoo.py` is a notebook task whose first cell is
  `%pip install yfinance==1.7.0` (the version the probes proved), then
  `dbutils.library.restartPython()`. It is the only notebook allowed `%pip`;
  CLAUDE.md's guardrail records the exception. Widgets: `catalog`,
  `workspace_file_path`, `reload_symbols` (default empty), `run_id`
  (`{{job.run_id}}`).
- **D2 Helpers** in `src/common/yahoo_market.py` (symbol mapping, rows from
  the pandas results, start date and reload rule, monthly expiry, JSON Lines),
  unit tested without network; the notebook only calls `yfinance`, reads and
  writes state, and writes files.
- **D3 Incremental prices; reload on events** (user, 2026-10-29).
  - Normal fetch: from (last stored price date - 1 day) to today, with
    `actions=True`. The overlap rewrites a day stored while the market was
    open. Symbols with the same start date are fetched in one bulk download.
  - Reload, for one symbol: from its first stored price date (one year back
    for a new symbol) to today, plus `Ticker.actions` (its full dividend and
    split history). Triggers: no state row; a dividend or split in the newly
    fetched days (Yahoo restated every earlier adjusted close, or every price
    and dividend); the symbol named in `reload_symbols` (`*` for all).
    Reloading from the first stored date, not one year, keeps every stored
    day's adjusted close consistent.
  - About 30 to 40 payers go ex-dividend in a week: about 2,500 new price rows
    plus about 10,000 reloaded rows a week, against 127,000 for a full weekly
    re-fetch.
  - Rejected: comparing a stored close with the refetched one to detect a
    restatement (events cover it, and `reload_symbols` covers anything else);
    a full re-fetch every week (raw grows 8 million rows a year).
- **D4 Files and columns.** `/Volumes/<catalog>/bronze_yahoo/s3_raw/<dataset>/landing/<YYYY-MM-DD>/<dataset>_<fetch time>_<batch>.jsonl`.
  Every row carries `symbol` (index symbol), `yahoo_symbol` and
  `ingested_timestamp` (the notebook's fetch time). Columns:
  - prices: `date`, `open`, `high`, `low`, `close`, `adj_close`, `volume`;
  - events: `date`, `event_type` (`dividend` or `split`), `value` (amount or
    ratio). Dividend dates carry a New York time of 09:30 (P1); the date part
    in New York time is the ex-date;
  - calendar: `ex_dividend_date`, `dividend_date` (Yahoo's name for the pay
    date), `earnings_date` (the first of Yahoo's list); the estimates Yahoo
    also sends are not kept;
  - options: `has_options`, `expiry_count`, `nearest_monthly_expiry`,
    `open_interest` and `volume` (calls plus puts on that expiry, both as
    sent). P1 found open interest 0 on every strike, even for AAPL, while
    volume is filled in; silver decides which to use.
- **D5 Monthly expiry** = the first expiry on or after the fetch date that is a
  Friday between the 15th and the 21st (the third Friday), as in the probe.
  None found: `nearest_monthly_expiry`, `open_interest` and `volume` empty,
  `has_options` still true if any expiry is listed.
- **D6 Fetch state and resuming** (user, 2026-10-29).
  - `bronze_yahoo.fetch_state`, a Delta table created and written only by the
    notebook (`CREATE TABLE IF NOT EXISTS`, `MERGE` per batch): `symbol`,
    `yahoo_symbol`, `first_price_date`, `last_price_date`, `last_run_id`,
    `last_fetched_timestamp`, `last_outcome` (`fetched`, `reloaded`,
    `no_prices`).
  - Batches of 50 symbols: fetch the four datasets, write their files, then
    merge the batch into the state. A failure between the write and the merge
    refetches that batch on repair; the keys in D8 absorb the repeated rows.
  - A repair of the same job run keeps `{{job.run_id}}`, so the notebook skips
    symbols whose `last_run_id` is this run. A new run fetches every symbol
    (cheap, D3). Rejected: "not fetched for 6 days" (breaks when the schedule
    changes); marking every symbol "running" at the start (finishing marks
    already say what is left).
  - The state is operational, not source data: it is not in raw, not
    replayed, and a lost state only means one full reload.
- **D7 Tolerated gaps.** At the end, the run fails if more than 2% of current
  S&P 500 members got no prices; files already written stay, and a repair
  retries the symbols not fetched. Former members and benchmarks with no
  prices are logged (`no_prices`) and never counted. Per-symbol errors in
  events, calendar and options are counted and logged; the exit message
  reports every count.
- **D8 Bronze raw and Publish.**
  - Raw as SEC: explicit all-text schema, `rescuedDataColumn`,
    `ingested_timestamp` cast to timestamp, `source_file_path`. Warn
    expectations: `symbol`, `date`, `close` (prices); `symbol`, `date`,
    `event_type`, `value` (events); `symbol` (calendar, options).
  - Publish by streaming `create_auto_cdc_flow` from raw, sequenced by
    `ingested_timestamp` (user, 2026-10-29: SCD1 is enough for prices):
    `prices_scd1` (`symbol`, `date`), `events_scd1` (`symbol`, `date`,
    `event_type`), `options_scd1` (`symbol`), `calendar_scd2` (`symbol`,
    history excluding `ingested_timestamp` and `source_file_path`). Raw keeps
    every file, so older values are never lost. Change data feed on.
  - `cluster_by_auto` on `prices_raw` and `prices_scd1`.
  - A symbol that stops being fetched keeps its last rows; silver decides.
  - Bronze verification compares the distinct keys of raw with Publish (no
    `compare_latest_file_per`: each file holds only part of the data).
- **D9 Benchmarks** come from a new `portfolio` dataset, `benchmarks`
  (`data/portfolio/benchmarks.csv`, key `symbol`; columns `name`, `kind`,
  `sector`), loaded like the other `portfolio` datasets. Rows: SPY (market),
  NOBL (dividend), `^VIX` (volatility, prices only), and the 11 SPDR sector
  funds XLK, XLF, XLV, XLE, XLI, XLY, XLP, XLU, XLB, XLRE, XLC, each with its
  GICS sector as Wikipedia writes it.
- **D10 Pipelines and job** as SEC: `bronze--yahoo--<target>`,
  `silver--yahoo--<target>`, job `run_yahoo` with `fetch` first. `yahoo` sorts
  after `wikipedia` and `portfolio`, so CI's alphabetical run order already
  runs its inputs first.

## Probes

- **P1 Keys and shapes** (done 2026-10-28,
  `references/poc/dividend-portfolio/p8_yahoo_shapes.py`, 20 symbols on
  serverless): prices 251 trading days per symbol, `symbol, date` unique, no
  empty key, columns Open, High, Low, Close, Adj Close, Volume; dividends
  `symbol, ex_date` unique (BRK-B, AMZN and TSLA pay none), ex-date at 09:30
  New York time; calendar fields `Dividend Date` (pay date) and
  `Ex-Dividend Date` (dates), `Earnings Date` (a list), plus estimates; ETFs
  return an empty calendar; options listed for all 20, open interest 0 on
  every AAPL strike while volume is filled in. Times for 20 symbols: prices
  2.8 s, dividends 6.6 s, calendar 2.1 s, options 3.3 s.
- **P2 Incremental, repair and reload in dev** (task 4): first run (every
  symbol reloaded); second run (only new days, plus symbols with an event);
  a run with `reload_symbols` `AAPL`; a run cancelled after a few batches and
  repaired (`{{job.run_id}}` kept, remaining symbols only). Record rows per
  dataset and times.

## Risks / Trade-offs

- [`yfinance` breaks or Yahoo blocks] → the 2% rule fails the run; the
  version is pinned; P6 showed no blocking.
- [Yahoo restates history without a dividend or split (a correction)] →
  not detected; `reload_symbols` fixes a known case.
- [A former member's symbol is reused by another company] → its new prices
  continue the old series; silver's company dimension decides (by SEC key).
- [`fetch_state` is lost] → the next run reloads every symbol; raw and Publish
  absorb it by key.
- [The calendar has a pay date only after a dividend is announced] → the SCD2
  versions build the history from the first load; silver estimates the rest.

## Migration Plan

Deploy to dev; run `run_portfolio` (new `benchmarks`), then `run_yahoo` with
`verify=true`, then the P2 runs. Stop the SQL warehouse after query sessions.
prd: CI deploys on merge and runs the affected units (portfolio, yahoo; yahoo
sorts after its inputs). Rollback: remove the resources and `fetch_state`;
files stay in the volume.
