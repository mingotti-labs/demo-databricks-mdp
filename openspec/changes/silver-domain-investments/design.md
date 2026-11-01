## Context

Six sources of the dividend story are in `silver_landing` (counts in prd,
2026-10-31):

| Landing table | What it holds | Shape |
|---|---|---|
| `wikipedia__sp500_constituents` | 503 symbols, 500 CIKs; sector, sub-industry, date added | SCD2 (`is_current`, `scd_valid_*`), text |
| `sec__company_facts` | about 1.3 million facts for 46 mapped concepts; `cik, taxonomy, concept, unit, start, end, val, fy, fp, form, filed, accn` | SCD2, text |
| `yahoo__prices` | 130,273 rows, 517 symbols, 2025-10-29 to 2026-10-30 | text, `symbol` with dots |
| `iso__market_identifier_codes` (new, `iso-mic` change) | ISO 10383 list: 1,596 operating markets and 1,293 segments | SCD2 text; name to be set in that change |
| `yahoo__events` | 50,548 dividends (433 symbols, from 1962), 1,517 splits | text |
| `yahoo__calendar` | next ex-date and pay date per symbol | SCD2, text |
| `yahoo__options` | options flag and activity per symbol | text |
| `rba__observations`, `fred__observations` | `FXRUSD` (A$1 in USD, from 2023-01-03), `FIRMMCRTD`, `DGS10`, `DFF`, `DFEDTARU`, `DFEDTARL` | long, `observation_date` DATE, `value` text |
| `portfolio__*` | concept mapping, predecessor CIKs, settings, benchmarks | SCD2, text |

The empty schema `silver_investments` existed in dev and prd (iac
`dividend-portfolio-schemas`) and is replaced by `silver_domain_investments`
(iac `silver-domain-investments-schema`). The metastore held 446 of 500 table slots on
2026-10-31; the working stop line is 488.

## Goals / Non-Goals

**Goals:**
- Typed, joined tables that gold can read without touching Landing.
- Every SEC figure traceable to the concept and filing it came from.
- The inputs NCAV and Graham's Number need, in `company_fundamentals`, as
  they were known on each date (point in time).

**Non-Goals:**
- Metrics of any kind (yield, growth, payout, NCAV, Graham's Number): gold.
- A per-company pay-date offset: the settings default only.
- `transformed_timestamp` (see Decisions).

## Decisions

### Materialized views, one pipeline, full recompute
Every table is a materialized view in one serverless pipeline that reads
`silver_landing` by qualified name. The inputs are small (the largest is SEC at
about 1.3 million rows), the tables join several sources, and some rows depend
on others (special dividends, validity ranges), which a streaming table
cannot express. Alternative: streaming tables over the Landing change feeds.
Rejected: joins across sources and window rules over history do not fit an
append-only stream, and the volume does not need it.

### Timestamps: `ingested_timestamp` only
Each row carries the Landing row's `ingested_timestamp`, or the earliest of its
inputs when a row combines several (NAMING.md, aggregating tables). There is no
`transformed_timestamp`: NAMING.md stamps it only where a step detects a
change, and a materialized view recompute cannot tell which rows changed.
Alternative: the Silver Normalised rebuild that keeps previous stamps. Rejected
for now: it needs a job task outside the pipeline and nothing downstream needs
the column yet. Recorded in NAMING.md's status line.

### Keys and names
- `company_id` is `sha2(concat_ws(':', identifier_source, central_index_key), 256)`
  (user, 2026-10-31): opaque, 64 hex characters, identical on every rebuild, and
  another registry hashes its own source name and number. The source and number
  stay as columns (`identifier_source`, `central_index_key`); nobody parses the
  id. `listing_id` is `sha2(concat_ws(':', market_identifier_code,
  trading_symbol_code), 256)`. Counter keys were rejected: a full recompute would
  renumber them. Readable composite keys were rejected by the user: an id
  carries no meaning. `concat_ws` skips empty parts, so a benchmark with no
  market hashes its symbol alone until the world indexes change adds the market.
- **Where ids live** (user, 2026-10-31): entity ids belong in the Silver Domain,
  warehouse surrogate keys in gold. Landing and Normalised keep each source's own
  keys (CIK, symbol, ABN); the domain layer is where sources become one set of
  entities, so it defines one stable identity per entity, or every gold table
  would re-solve "which CIK is this symbol" and could drift. An entity id
  (`company_id`, `listing_id`) identifies the thing itself and is a hash of its
  business key. A dimension surrogate key is one per version of a dimension row
  (SCD2) so facts point at the row true at the time; that comes from how gold
  shapes a model, so gold adds it when it builds a versioned dimension. The
  weakness of a hash: if the business key changes (a reissued CIK, a company
  later matched to a second registry) the id changes. A stored counter with a
  crosswalk table survives that but needs state that outlives a rebuild, which
  materialized views cannot hold. Revisit with a persistent crosswalk when
  companies are matched across registries (for example an ASX company that also
  files with the SEC); the column names do not change. The predecessor-CIK rule
  covers the one such case known today.
- Tables are named for what a row is; a grain suffix is added when one entity
  has a row per period (`price_daily`, `market_rate_daily`). `market_rate_daily`
  holds exchange and interest rates in one table; gold can split them into
  separate facts later (user, 2026-10-31). `company_fundamentals` is
  the user's name (2026-10-31): a row is the company's fundamentals as reported
  on one date.
- `trading_symbol_code` keeps the Wikipedia form with dots (`BRK.B`), as every
  Landing table does (the Yahoo Landing tables already use it, so prices join on
  the exact string); the Yahoo form stays in the raw data.
- No abbreviations in names: `central_index_key`, `earnings_per_share`,
  `earnings_before_interest_tax_depreciation_amortisation`,
  `amount_in_australian_dollars`, `sector` and `sub_industry` (not `gics_*`).
  `rate_code` values are spelled out the same way. Cryptic names that stay are
  translated in gold.
- Resource key `silver_domain_investments`, display name
  `silver--domain--investments--<target>`, unit `run_investments`
  (`run--investments--<target>`).

### Company, market, listing and membership
`company` groups every Wikipedia version by central index key: the name and
sector of the key's current version (or its latest when it left), with share
classes resolved by taking the alphabetically first symbol's name. It has no
index columns. `market` selects the operating markets (`OPRT`) of the ISO list.
`listing` has a row per symbol seen in the Wikipedia versions (market from Yahoo's exchange code, probe P2) and per `portfolio` benchmark; `company_id` comes from the symbol's latest
Wikipedia version, so a symbol reused by another company would be assigned to
the latest one (the verification fails if one symbol maps to two keys, so the
gap is visible, not silent). `index_membership` is a typed copy of the Wikipedia
SCD2 versions with `index_code` `SP500` and `listing_id`.

#### How company, prices and the rest connect
SEC facts hold the central index key; Yahoo holds the symbol; the Wikipedia list
holds both. So: `price_daily.listing_id = listing.listing_id`, and
`listing.company_id = company.company_id`, where `listing` takes the central
index key from Wikipedia. A company that was never in the S&P 500 has no join to
Yahoo; the hierarchy `financial_instrument`, `security`, `listing` is the user's
model (2026-10-31), but only `listing` exists, so the trading symbol code is an
attribute of the listing for now.

### Prices
`price_daily` types `yahoo__prices` and keeps `listing_id`, `close` (Yahoo's raw close),
`volume` and `currency_code`. The adjusted close is dropped, as the story
decided (raw close plus dividend events). `currency_code` is `USD` for every
symbol now; the world indexes change adds a currency to the benchmarks and
replaces that constant.

### Dividends
- Amount as Yahoo reports it. Yahoo adjusts dividends for later splits, so
  amounts over time compare like for like.
- `amount_in_australian_dollars = amount / FXRUSD` at the latest RBA date on or before the
  ex-date (an as-of join). RBA's held history starts 2023-01-03, so older
  dividends have no AUD amount; the trailing-12-months yield needs only recent
  ones. Loading RBA's historical F11.1 file is a later RBA change if needed.
- Pay date: the Yahoo calendar's `dividend_date` from any calendar version
  whose `ex_dividend_date` equals the ex-date; otherwise ex-date plus
  `pay_date_offset_days` from `portfolio__settings` (current version).
- `is_special`: amount more than twice the median of the symbol's previous four
  dividends (a window over ex-dates). A first dividend is never special. The
  factor is a constant in code for now, not a setting, until it proves useful.

### Fundamentals per filing (`company_fundamentals`)
The user's grain (2026-10-31): one row per company and reported date, so gold
can ask "what did we know on date X". `valid_from_date` is the SEC `filed` date
of the filing; with `company_id` it is the business key. `valid_to_date` is the
next row's `valid_from_date` minus one day (a `lead` over the company's rows),
or 9999-12-31 for the latest. SEC Landing already holds the 10-Q facts (about
725,000 current rows), so no new source is needed. In this order, all on
current SEC versions:
1. Keep facts whose `form` is `10-K`, `10-K/A`, `10-Q` or `10-Q/A`, with unit
   `USD`, `shares` or `USD/shares`. Other currencies (about 40 facts) and other
   forms (8-K, proxy statements) are left out.
2. A filing is one accession number (`accn`). Its period end is the latest
   `end` among its facts; its form and `filed` date are its own. Two filings of
   one company on the same day keep the later accession number.
3. Balance sheet figures and the share count: the filing's own facts dated at
   its period end. The cover-page share count
   (`dei:EntityCommonStockSharesOutstanding`) is dated at the filing, weeks
   after the period end, so it is taken from the same filing whatever its date.
   Which figures are balance sheet (instant) is a property of the figure,
   listed in code next to the mapping columns.
4. Income and cash flow figures, trailing twelve months to the period end:
   - from a 10-K: the facts about a year long (330 to 380 days) ending at the
     period end;
   - from a 10-Q: this filing's year-to-date fact (starting at the fiscal year
     start) plus the latest annual value known on the filing date minus the
     prior year's year-to-date (the comparative in the same 10-Q). Empty when
     any of the three is missing. Earnings per share uses the same sum, an approximation since
     the share count changes between periods.
   SEC's `fy` labels the comparative periods inside a filing too, so periods
   are identified by `start` and `end`, never by `fy`.
5. Per filing and figure, the concept with the lowest priority number that has
   a value. The choice is per filing, so a company that switched concepts keeps
   a continuous series.
6. `total_liabilities` falls back to `liabilities_and_equity - total_equity`
   when no `Liabilities` value exists; the concept map records `derived`.
7. Predecessors: filings of a predecessor CIK, dated before the successor's
   first filing, are relabelled with the successor's `company_id`.
8. Derived columns: `free_cash_flow`, `total_debt` (long plus short, either
   alone when the other is missing),
   `earnings_before_interest_tax_depreciation_amortisation`.

Point in time means a restatement never changes an earlier row: a 10-K/A is a
new row from its own filing date. Alternative considered: one row per fiscal
year with the latest restated values. Rejected by the user: it hides what was
known when, and quarterly balance sheets make NCAV current.

Size: about 500 companies, four filings a year since XBRL began (2009): about
35,000 rows.

The wide table has one column per figure, a fixed list in code that a test
compares with `concept_mapping.csv`, so a figure added to the CSV without a
column fails the test rather than vanishing. `concept_used` is a
`MAP<STRING, STRING>` (figure to concept). Alternative: a long table (one row
per figure). Rejected: every gold metric would pivot it again, and a fixed
column list is what Genie reads best.

The pure parts (choosing the concept by priority, the trailing-twelve-months
sum, the duration check, the validity dates, the special-dividend rule) are Python functions in
`src/common/investments.py` that build Spark column expressions or work on
plain rows, with unit tests. The pipeline files only wire them.

### New mapping rows

| figure | priority | concept |
|---|---|---|
| `current_assets` | 1 | `AssetsCurrent` |
| `total_liabilities` | 1 | `Liabilities` |
| `liabilities_and_equity` | 1 | `LiabilitiesAndStockholdersEquity` |
| `stockholders_equity` | 1 | `StockholdersEquity` |
| `stockholders_equity` | 2 | `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |
| `total_equity` | 1 | `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |
| `total_equity` | 2 | `StockholdersEquity` |
| `preferred_stock` | 1 | `PreferredStockValue` |
| `earnings_per_share` | 1 | `EarningsPerShareDiluted` |
| `earnings_per_share` | 2 | `EarningsPerShareBasic` |

`stockholders_equity` (book value for Graham's Number) prefers the parent's
equity; `total_equity` (for the liabilities fallback) prefers the figure that
includes non-controlling interests, because `LiabilitiesAndStockholdersEquity`
includes them.

### Market rates
`market_rate_daily` selects six series from the two Landing tables by a fixed list in
code (`rate_code`, source, series id, unit): `australian_dollar_in_us_dollars`,
`rba_cash_rate_target`, `us_10_year_treasury_yield`,
`us_federal_funds_effective_rate`, `us_federal_funds_target_upper`,
`us_federal_funds_target_lower`. The other RBA and FRED series stay in Landing; adding one is
one line.

### Options
`options_activity` is the latest row per listing of `yahoo__options`, typed.

### Verification
`verification/verify_silver_domain_investments.py`, run only by
`run_investments` (not shared, so it never makes CI run other units), with the
checks the spec lists. It does not use the Landing checks files: those count
Landing against Bronze, which does not apply here.

### Table quota
Nine materialized views cost 2 slots each per target: 36 slots, about 482 of
500 after (446 on 2026-10-31), and the `iso-mic` source adds about 12 more.
Merging `options_activity` into another table was considered and rejected: no
other table has its grain (one row per listing, now). Both changes together
pass the 488 stop line, so a clean-up change must land before the second of
them deploys; candidates are listed in the risk below, not chosen here.

## Probes

- **P2, the market of each S&P 500 symbol** (done 2026-10-31; scripts and result
  in `references/poc/silver-domain-investments/`): SEC's
  `company_tickers_exchange.json` (10,430 tickers; `exchange` is `Nasdaq`, `NYSE`
  or `CBOE`) and Yahoo's `fast_info["exchange"]` (`NMS`, `NYQ`, `BTS`) both cover
  all 503 current members and agree on every one once mapped to operating market
  identifier codes: 345 `XNYS`, 157 `XNAS`, 1 `XCBO` (Cboe Global Markets itself).
  Decision: the market comes from Yahoo, carried on the calendar row the Yahoo
  fetch already writes for every symbol (`exchange_code`, a column on
  `yahoo__calendar`, SCD2 so a move between markets keeps its history), and
  `src/common/investments.py` maps it to the operating code. This adds no table,
  where a new SEC source would cost a raw, Publish and Landing table (12 slots).
  Cost: `fetch_yahoo.py` changes, so CI runs `run_yahoo`, and every calendar row
  gets one new version once (the column is new). SEC stays the cross-check, not
  the source. Mapping: `NMS`, `NGM`, `NCM` to `XNAS`; `NYQ`, `PCX`, `ASE` to
  `XNYS`; `BTS` to `XCBO`; `CXI` (the Cboe Volatility Index benchmark `^VIX`, found when
  `run_yahoo` ran in dev) to `XCBO`, as Cboe's operating market. The ISO list gives `BATS`, `ARCX` and `XASE` as
  segments of `XCBO` and `XNYS`, and `market` holds operating markets only, so
  the mapping goes to the operating code. A code with no mapping fails the
  verification.
- **P1, SEC coverage of the new concepts** (done 2026-11-01; `p1_coverage.py` and
  `p1_result.txt`): of the 500 current CIKs, a 10-K ending in the last 18 months
  has `AssetsCurrent` for 417 (83 without: banks, insurers and similar),
  `Liabilities` for 358, `LiabilitiesAndStockholdersEquity` for 497,
  `StockholdersEquity` for 465, the including-non-controlling-interest equity
  for 308, `PreferredStockValue` for 219 and earnings per share for 480. The
  liabilities fallback is needed for 142 companies and its inputs exist for 139;
  3 have no balance sheet total. `preferred_stock` stays (219 companies). Original question: (before the mapping rows are
  merged): for every current CIK, which of the new concepts appear in a 10-K
  for a fiscal year ending in the last 18 months. Answers how often the
  liabilities fallback is needed and whether `preferred_stock` is worth keeping.
  Scripts in `references/poc/silver-domain-investments/`.

## Risks / Trade-offs

- [Banks and insurers have no classified balance sheet, so no
  `current_assets`] → the column is empty for them; gold leaves NCAV empty.
- [A company tags a figure with a concept outside the mapping] → the column is
  empty; the verification's net income coverage check catches the common case;
  more concepts are a CSV change.
- [`dei:EntityCommonStockSharesOutstanding` counts one class only for some
  multi-class companies] → known gap; per-share metrics in gold flag it, not
  fixed here.
- [Table quota: about 482 after, plus `iso-mic`, gold needs more] → before the gold change,
  a clean-up change; candidates: the dev-only pattern pipelines' tables, the
  human-owned neon and clickstream dev copies (15 tables), orphan
  materialization twins.
- [Merging the mapping change rewrites every SEC facts file once] → about 500
  files appended to the raw volume, a one-off.
- [`currency_code` constant `USD`] → right for S&P 500 members and current
  benchmarks; the world indexes change replaces it, and adds the market to
  each benchmark.
- [`listing` has no `security` or `financial_instrument` above it] → share
  classes are separate listings tied by `company_id`; cross-listings of one
  share are separate rows until those tables exist.

## Migration Plan

1. iac `silver-domain-investments-schema` applied (new schema and grants, old
   empty schema dropped) in both workspaces' deployments. The `iso-mic` change
   implemented and its Landing table loaded.
2. Probes P1 and P2.
3. Mapping rows merged in the implementation PR; in dev, `run_portfolio` then
   `run_sec` load the new concepts.
4. Pipeline and job deployed by the PR; `run_investments` in dev with
   `verify=true`.
5. Merge: CI runs `run_investments` and `run_portfolio` in prd. `run_sec` is
   not selected by CI (the mapping is read at run time), so the new columns are
   empty in prd until `run_sec` and then `run_investments` run once by hand, one
   at a time, with the user's approval.

Rollback: delete the pipeline (its tables go with it) and revert the mapping
rows; nothing upstream changes.

## Dev results (2026-11-01)

Run as the service principal after `run_portfolio`, `run_sec` and `run_yahoo`.

- **Counts:** `company` 500, `market` 1,596, `listing` 517, `index_membership`
  503, `price_daily` 130,787, `dividend` 50,548, `company_fundamentals` 30,655
  (499 companies), `market_rate_daily` 60,635, `options_activity` 517. Prices,
  dividends and options equal their Landing tables row for row.
- **Entities:** `GOOGL` and `GOOG` are two listings of one company (named after
  `GOOG`, the alphabetically first symbol). All 517 current calendar rows carry an
  exchange code: `NYQ` 345, `NMS` 157, `PCX` 12, `BTS` 2, `CXI` 1. `CXI` is the Cboe
  Volatility Index benchmark `^VIX`, not covered by probe P2 (members only); it
  maps to `XCBO`. Verification found it on the first run.
- **Dividends:** 300 pay dates come from Yahoo's calendar (for example `STZ`
  2026-10-30 ex, 2026-11-13 pay, equal to Landing) and 50,248 are the ex-date plus
  14 days; no dividend since 2023-01-03 lacks an Australian dollar amount. 607
  are `is_special`. The rule flags step changes too: `NVDA` went from 0.01 to 0.25
  in 2026, and both 0.25 payments are flagged, because the median of the previous
  four stays at 0.01 for the second one. Real one-offs are also flagged (`TDG`
  90.00, `CME` 5.80 and 7.45, `PGR` 13.60). Gold decides what to do with it.
- **Rates:** six `rate_code` values; latest cash rate 4.60 and 10-year 4.98 on
  2026-10-29.
- **Fundamentals:** 499 current rows (`Vylor`, a new central index key, has no
  filings yet); 496 of 499 had `net_income` on the first run, 497 after the
  predecessor fix. The two without are Honeywell Aerospace (a new spin-off, one
  filing) and Viatris. 141 current rows use the liabilities fallback. ExxonMobil's
  successor holds 70 filings back to 2009 from its predecessor; its trailing twelve
  months first lacked a value because the annual figure was under the
  predecessor's key, fixed by joining annual values on the successor key.
- **By hand against the raw facts:** Apple's latest 10-Q net income 128,930
  million = 112,010 (FY2025) + 101,464 (nine months) - 84,544 (prior nine
  months); JPMorgan Chase has no current assets and liabilities 4,640 billion +
  equity 374.6 billion = total 5,015 billion; Lilly has no `Liabilities`, so
  148,072 - 40,271 = 107,801 million is derived and marked `derived`.
- **Verification:** the first run failed on the `^VIX` market only, naming it;
  after the `CXI` mapping every check passed.
- **Deliberate failure:** `run_investments` with `verify=true` and
  `check_symbol=ZZZZ` failed with `symbol ZZZZ has no listing: ['ZZZZ']`; without
  the parameter the next run passed.
- **Quota:** 459 live after the dev deploy (440 before: 18 for the nine views, 1
  for the pipeline's event log). The prd deploy adds the same 19, about 478 of 500,
  under the 488 stop line.
