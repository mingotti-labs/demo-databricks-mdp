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
- The inputs NCAV and Graham's Number need, in `fundamental_annual`.

**Non-Goals:**
- Metrics of any kind (yield, growth, payout, NCAV, Graham's Number): gold.
- Latest-twelve-months and quarterly figures: annual only. Graham's Number
  and NCAV in gold start from the latest fiscal year.
- A per-company pay-date offset: the settings default only.
- `transformed_timestamp` (see Decisions).

## Decisions

### Materialized views, one pipeline, full recompute
Every table is a materialized view in one serverless pipeline that reads
`silver_landing` by qualified name. The inputs are small (the largest is SEC at
about 1.3 million rows), the tables join several sources, and some rows depend
on others (special dividends, predecessor years), which a streaming table
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
- Tables are singular entity names; a grain suffix is added when one entity
  has a row per period (`price_daily`, `fundamental_annual`, `rate_daily`).
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

### Fundamentals: applying the concept mapping
In this order, all on current SEC versions:
1. Keep facts whose `form` is `10-K` or `10-K/A` and `fp` is `FY`, with unit
   `USD`, `shares` or `USD/shares`. Other currencies (about 40 facts) are left
   out.
2. Duration figures (income and cash flow) need `start` and `end` about a year
   apart (330 to 380 days); instant figures (balance sheet, shares) have no
   `start`. Which figures are instant is a property of the figure, listed in
   code next to the mapping columns.
3. The fiscal year is identified by its end date: the `end` of the duration
   facts. SEC's `fy` is the filing's year and also labels the comparative
   years inside a filing, so it is not used.
4. Per company, concept and period, keep the value with the latest `filed`
   (a restatement in a later 10-K wins).
5. Per company, figure and fiscal year end, take the concept with the lowest
   priority number that has a value. The choice is per year, so a company that
   switched concepts keeps a continuous series.
6. Instant figures are matched to the fiscal year end on the same date. The
   cover-page share count (`dei:EntityCommonStockSharesOutstanding`) is dated
   at the filing, weeks after the year end, so it is matched to the latest
   fiscal year end within 120 days before its date, from the same filing
   (`accn`).
7. `total_liabilities` falls back to `liabilities_and_equity - total_equity`
   when no `Liabilities` value exists; the concept map records `derived`.
8. Predecessors: facts of a predecessor CIK are relabelled with the successor's
   `company_key` and used only for fiscal years the successor has none of its
   own.
9. Derived columns: `free_cash_flow`, `total_debt` (long plus short, either
   alone when the other is missing), `ebitda`. EPS stays as reported
   (`EarningsPerShareDiluted`, else `Basic`).

The wide table has one column per figure, a fixed list in code that a test
compares with `concept_mapping.csv`, so a figure added to the CSV without a
column fails the test rather than vanishing. `concept_used` is a
`MAP<STRING, STRING>` (figure to concept). Alternative: a long table (one row
per figure). Rejected: every gold metric would pivot it again, and a fixed
column list is what Genie reads best.

The pure parts (choosing the concept by priority and filing date, the
duration check, the special-dividend rule) are Python functions in
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

### Rates
`rate_daily` selects six series from the two Landing tables by a fixed list in
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
