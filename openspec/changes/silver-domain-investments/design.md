## Context

Six sources of the dividend story are in `silver_landing` (counts in prd,
2026-10-31):

| Landing table | What it holds | Shape |
|---|---|---|
| `wikipedia__sp500_constituents` | 503 symbols, 500 CIKs; sector, sub-industry, date added | SCD2 (`is_current`, `scd_valid_*`), text |
| `sec__company_facts` | about 1.3 million facts for 46 mapped concepts; `cik, taxonomy, concept, unit, start, end, val, fy, fp, form, filed, accn` | SCD2, text |
| `yahoo__prices` | 130,273 rows, 517 symbols, 2025-10-29 to 2026-10-30 | text, `symbol` with dots |
| `yahoo__events` | 50,548 dividends (433 symbols, from 1962), 1,517 splits | text |
| `yahoo__calendar` | next ex-date and pay date per symbol | SCD2, text |
| `yahoo__options` | options flag and activity per symbol | text |
| `rba__observations`, `fred__observations` | `FXRUSD` (A$1 in USD, from 2023-01-03), `FIRMMCRTD`, `DGS10`, `DFF`, `DFEDTARU`, `DFEDTARL` | long, `observation_date` DATE, `value` text |
| `portfolio__*` | concept mapping, predecessor CIKs, settings, benchmarks | SCD2, text |

The empty schema `silver_investments` exists in dev and prd (iac
`dividend-portfolio-schemas`). The metastore held 446 of 500 table slots on
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
- `company_key` is `sec_cik:<10-digit CIK>`: readable, stable across reloads
  and leaves room for `asx:<code>` later. Surrogate integer keys were rejected:
  a full recompute would renumber them.
- Tables are named for what a row is; a grain suffix is added when one entity
  has a row per period (`price_daily`, `market_rate_daily`). `market_rate_daily`
  holds exchange and interest rates in one table; gold can split them into
  separate facts later (user, 2026-10-31). `company_fundamentals` is
  the user's name (2026-10-31): a row is the company's fundamentals as reported
  on one date.
- `symbol` keeps the Wikipedia form with dots (`BRK.B`), as every Landing table
  does; the Yahoo form stays in Landing.
- Resource key `silver_domain_investments`, display name
  `silver--domain--investments--<target>`, unit `run_investments`
  (`run--investments--<target>`).

### Company and membership
`company` groups every Wikipedia version by CIK: the name and sector of the
CIK's current version (or its latest when it left), with share classes resolved
by taking the alphabetically first symbol's name; `in_index` is any current
version. `index_membership` is a typed copy of the Wikipedia SCD2 versions with
`index_code` `SP500` and `company_key`.

### Prices
`price_daily` types `yahoo__prices` and keeps `close` (Yahoo's raw close),
`volume` and `currency_code`. The adjusted close is dropped, as the story
decided (raw close plus dividend events). `currency_code` is `USD` for every
symbol now; the world indexes change adds a currency to the benchmarks and
replaces that constant.

### Dividends
- Amount as Yahoo reports it. Yahoo adjusts dividends for later splits, so
  amounts over time compare like for like.
- `amount_aud = amount / FXRUSD` at the latest RBA date on or before the
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
of the filing; with `company_key` it is the business key. `valid_to_date` is the
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
     any of the three is missing. EPS uses the same sum, an approximation since
     the share count changes between periods.
   SEC's `fy` labels the comparative periods inside a filing too, so periods
   are identified by `start` and `end`, never by `fy`.
5. Per filing and figure, the concept with the lowest priority number that has
   a value. The choice is per filing, so a company that switched concepts keeps
   a continuous series.
6. `total_liabilities` falls back to `liabilities_and_equity - total_equity`
   when no `Liabilities` value exists; the concept map records `derived`.
7. Predecessors: filings of a predecessor CIK, dated before the successor's
   first filing, are relabelled with the successor's `company_key`.
8. Derived columns: `free_cash_flow`, `total_debt` (long plus short, either
   alone when the other is missing), `ebitda`.

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
| `eps` | 1 | `EarningsPerShareDiluted` |
| `eps` | 2 | `EarningsPerShareBasic` |

`stockholders_equity` (book value for Graham's Number) prefers the parent's
equity; `total_equity` (for the liabilities fallback) prefers the figure that
includes non-controlling interests, because `LiabilitiesAndStockholdersEquity`
includes them.

### Market rates
`market_rate_daily` selects six series from the two Landing tables by a fixed list in
code (`rate_code`, source, series id, unit): `aud_usd`, `rba_cash_rate_target`,
`us_10y_treasury`, `fed_funds_effective`, `fed_target_upper`,
`fed_target_lower`. The other RBA and FRED series stay in Landing; adding one is
one line.

### Options
`options_activity` is the latest row per symbol of `yahoo__options`, typed.

### Verification
`verification/verify_silver_domain_investments.py`, run only by
`run_investments` (not shared, so it never makes CI run other units), with the
checks the spec lists. It does not use the Landing checks files: those count
Landing against Bronze, which does not apply here.

### Table quota
Seven materialized views cost 2 slots each per target: 28 slots, about 474 of
500 after. Merging `options_activity` into another table was considered and
rejected: no other table has its grain (one row per symbol, now). The gold
change after this one needs a clean-up first; candidates are listed in the risk
below, not chosen here.

## Probes

- **P1, SEC coverage of the new concepts** (before the mapping rows are
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
- [Table quota: about 474 after, gold needs more] → before the gold change,
  a clean-up change; candidates: the dev-only pattern pipelines' tables, the
  human-owned neon and clickstream dev copies (15 tables), orphan
  materialization twins.
- [Merging the mapping change rewrites every SEC facts file once] → about 500
  files appended to the raw volume, a one-off.
- [`currency_code` constant `USD`] → right for S&P 500 members and current
  benchmarks; the world indexes change replaces it.

## Migration Plan

1. iac `silver-domain-investments-schema` applied (new schema and grants, old
   empty schema dropped) in both workspaces' deployments.
2. Probe P1.
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
