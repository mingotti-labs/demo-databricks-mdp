# Yahoo Finance

Daily prices, dividends and splits, next pay dates and options activity, via
`yfinance` 1.7.0 (an unofficial client of Yahoo's public endpoints). Free, no
key; may break or rate-limit without notice.

- Symbols: every symbol ever in the Wikipedia S&P 500 history (a dot becomes a
  dash: `BRK.B` is `BRK-B`) plus the `portfolio` benchmarks (SPY, NOBL, `^VIX`,
  the 11 SPDR sector funds): 517 in the first load.
- Code: `src/common/yahoo_market.py` (plan, rows, monthly expiry),
  `src/common/fetch_yahoo.py` (first task of `run_yahoo`, the only notebook
  allowed `%pip`), `src/layers/bronze/yahoo/`, `src/layers/bronze/yahoo_publish/`,
  `src/layers/silver/landing/yahoo/`.

## How Yahoo restates history

Checked on NVDA's 10-for-1 split of 2024-06-10:

- `Close` (and open, high, low, volume) is split-adjusted: every earlier day is
  rewritten after a split.
- Dividend amounts are split-adjusted too (0.04 shows as 0.004).
- `Adj Close` is also adjusted for every later dividend: every earlier day
  changes when a symbol goes ex-dividend.

So a dividend or split in the new days reloads the symbol in full (prices from
its first stored day, all events); anything else Yahoo corrects needs the
`reload_symbols` job parameter.

## Files, state and tables

- The fetch notebook works in batches of 50 symbols and writes, per batch,
  `<dataset>/landing/<date>/<dataset>_<fetch time>_<batch>.jsonl` into
  `bronze_yahoo.s3_raw` for `prices`, `events`, `calendar`, `options`. Files are
  never overwritten or deleted.
- Prices are fetched from the last stored day minus one, so a day stored while
  the market was open is rewritten; a new symbol loads one year.
- `bronze_yahoo.fetch_state` (one row per symbol: first and last stored day,
  last run id, outcome) is written after each batch's files. A repair of the
  same job run skips symbols whose `last_run_id` is that run. Losing it only
  costs one full reload.
- Bronze Publish by streaming Auto CDC sequenced by the fetch time: SCD1 for
  prices, events, options; SCD2 for the calendar, whose platform columns are
  left out so an unchanged calendar writes no version.

## Shape and gotchas

- `yf.download(..., actions=True, group_by="ticker")` returns columns per
  ticker even for one symbol; dates are naive midnights. A symbol Yahoo does not
  know comes back with every value empty. `Ticker.actions` dates carry the
  exchange's time zone.
- `Ticker.calendar`: `Dividend Date` is the pay date, `Ex-Dividend Date` the
  ex-date, `Earnings Date` a list; ETFs and indexes return an empty calendar.
  The pay date is the last announced one, so it can be in the past.
- Option open interest is 0 on every strike (even AAPL) while volume is filled
  in; both are kept. `^VIX` options expire on Wednesdays, so it has no
  third-Friday expiry.
- First load (dev, 2026-10-29): 129,753 price rows, 52,048 events, 517 calendar
  and options rows; fetch 12.8 minutes. An incremental run: 1,034 price rows
  (two days per symbol), no calendar version; fetch 9.7 minutes, most of it the
  three per-symbol calls for calendar and options.
