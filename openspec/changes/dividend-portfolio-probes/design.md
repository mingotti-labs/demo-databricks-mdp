## Context

See proposal.md for why. The overall story design is in `demo-databricks-planning`
(`docs/superpowers/specs/2026-10-24-dividend-portfolio-story-design.md`), step 1
of "Order of changes". The iac change `dividend-portfolio-schemas` has created
the story's schemas, the `fmp` and `fred` secret scopes (READ for the CI/CD
service principal) and the `bronze_portfolio.s3_raw` volume.

Existing ingestion pipelines (acnc, ungm, iso, geonames, nsw_spatial, airroi)
already fetch from the internet on serverless, so outbound access works for
those hosts. Whether it works for the new hosts is not known.

## Goals / Non-Goals

**Goals:**
- Answer each question below with evidence from a real run on dev serverless.
- Decide the S&P 500 list source and the pay-date source for change 2 onwards.

**Non-Goals:**
- No tables, pipelines or jobs in the bundle. Results are printed by the probe
  runs and copied into this file.
- No RBA or FRED data probes beyond reaching the host: both are simple files or
  a documented API, and their own changes check the content.

## Decisions

- **D1 How the probes run.** Each probe is a plain Python file run as a one-time
  serverless job (`databricks jobs submit`, a `spark_python_task` with an
  environment listing its PyPI packages). The scripts are committed in
  `references/poc/dividend-portfolio/` (`p1_hosts.py` ... `p6_yahoo.py`, a README
  with how to run them) and uploaded to
  `/Workspace/Users/<user>/poc/dividend-portfolio/` for the runs.
  `references/**` is already excluded from the bundle upload, so they never
  deploy. Rejected: a top-level `poc/` folder (needs a new exclusion in both
  edition files and a regenerated `databricks.yml`); not committing them (a
  later change could not rerun or read them). This is the real shape (serverless, packages
  from the environment, outbound requests) except for identity: the run is the
  user's, not the CI/CD service principal's. The principal's READ on `fmp` is
  already confirmed by `databricks secrets list-acls fmp`; change 2 proves it in
  a real run. Rejected: running locally (different network and IP, the lesson
  from P6 in `correct-platform-timestamps`).
- **D2 One run per probe, in order, one at a time** (Free Edition). P1 first: a
  host that cannot be reached ends its probe there. P3 (Wikipedia) runs before
  P6 (Yahoo) because it supplies the ticker list.
- **D3 Call budgets.** FMP at most 15 calls; SEC at most 10 requests a second, a
  sample of 12 companies; Yahoo the full list once, which is the weekly shape.
- **D4 No secret printed.** The FMP key is read with `dbutils.secrets.get` and
  only response status, row counts and field names are printed. An FMP error
  body is printed with the key removed.
- **D5 SEC contact.** SEC asks for a `User-Agent` naming the app and a contact
  email. The user supplies the string for the probe; change 3 makes it a bundle
  variable (story design).

## Probes (dev)

- **P1 Reaching the hosts.** One GET each to `en.wikipedia.org`,
  `financialmodelingprep.com`, `www.sec.gov`, `data.sec.gov`,
  `query1.finance.yahoo.com`, `query2.finance.yahoo.com`, `www.rba.gov.au`,
  `api.stlouisfed.org`: status code and time, or the error.
- **P2 Metastore table count.** Tables per catalog from
  `system.information_schema.tables` (excluding `information_schema`), against
  the 500 limit, to size what the story can add.
- **P3 Wikipedia S&P 500 page.** Parse the `constituents` table on "List of S&P
  500 companies" with a `User-Agent`: row count, columns, CIK present and
  10-digit, "Date added" parse rate, share classes (GOOGL/GOOG), ticker format
  (`BRK.B`), and whether the "Selected changes" table also parses.
- **P4 FMP free plan.** With the key from the `fmp` scope:
  `stable/sp500-constituent` (on the plan? row count and fields);
  `stable/historical-sp500-constituent`; `stable/dividends?symbol=` for 5
  tickers (KO, O, JNJ, BRK-B, AAPL: are `paymentDate`, `recordDate`,
  `declarationDate` filled, and how far back); `stable/dividends-calendar` for
  one 90-day window (all symbols in one call: the cheaper path); any rate-limit
  headers. If a `stable` endpoint is refused, try its `api/v3` equivalent once.
- **P5 SEC company facts.** `company_tickers.json` (count, BRK-B form), then
  `companyfacts` for 12 companies across sectors (AAPL, MSFT, JNJ, KO, PG, XOM,
  JPM, NEE, O, T, ABBV, CB): which us-gaap concepts each has for the figures in
  the story design (net income, operating cash flow, capital expenditure,
  dividends paid, debt, cash, operating income, D&A, interest expense, shares
  outstanding), with the alternatives seen; latest fiscal year; response size.
  Also one `frames` call (one concept, one year, all companies) as the cheaper
  path.
- **P6 Yahoo (`yfinance`).** On P3's ticker list (dots changed to dashes):
  one bulk `yf.download` of 1 year of daily raw close; `Ticker.dividends` for
  every ticker; `Ticker.options` for every ticker; the nearest monthly option
  chain's open interest for 10 tickers. Time taken, tickers with no data, and
  any `429` or other blocking. Also whether `yf.download(period="max",
  actions=True)` returns the full dividend history in one bulk call, compared
  with `Ticker.dividends` for 5 tickers.

## Risks / Trade-offs

- [Yahoo blocks serverless IPs] → that is a valid result. The Yahoo change then
  needs another source for prices and dividends, decided before change 4.
- [The FMP free plan refuses the endpoints] → Wikipedia becomes the list source
  and pay dates are estimated, as the story design already allows.
- [A probe passes for the wrong reason] → each runs on serverless with the real
  key, packages and hosts; only the run identity differs (D1).
- [FMP calls count against the day] → at most 15 of 250; nothing else uses the
  key yet.

## Migration Plan

None: nothing is deployed. After the results are recorded, the uploaded
workspace folder is deleted (with the user's approval) and the one-time runs are
left in the job run history.

## Probe results

All run on 2026-10-25 in dev as one-time serverless jobs (environment version
4) from `references/poc/dividend-portfolio/` via `run.py`, one at a time. Two
probes were added while running: P4b (one more FMP call) and P6b (Yahoo pay
dates), both after P4 ruled FMP out.

- **P1 Reaching the hosts: pass.** Every host answered within 0.4 s:
  Wikipedia, SEC (`www` and `data`), Yahoo (`query1`, `query2`) and RBA with
  200; FMP 401 and FRED 400 because no key was sent, which still shows the host
  is reachable.
- **P2 Metastore table count: pass.** 301 tables: `mdp_dev` 175 (113 managed,
  46 streaming, 16 materialized views), `mdp_prd` 97, `samples` 28 (a shared
  catalog, probably not counted against the limit), `dbacademy` 1. Headroom
  about 200 to 230 tables.
- **P3 Wikipedia page: pass with a constraint.** The `constituents` table
  parses: 503 rows, 500 distinct CIKs (GOOGL/GOOG, FOXA/FOX, NWSA/NWS share
  one), columns Symbol, Security, GICS Sector, GICS Sub-Industry,
  Headquarters Location, Date added, CIK, Founded. Every date added parses
  (1957-03-04 to 2026-10-06). Constraints: CIK is zero-padded on the page but
  `read_html` turns it into a number (read it as text); `BRK.B` and `BF.B` use
  a dot where Yahoo uses a dash. The "Selected changes" table is no longer on
  the page (the only other table is a navigation box): membership history has
  to come from our own weekly snapshots, as the story design already planned.
  A first run was a probe error: a missing `id="changes"` table made pandas
  fall back to another parser and hide the real error.
- **P4 FMP free plan: fail.** 11 calls. `stable/sp500-constituent` and
  `stable/historical-sp500-constituent`: 402 "Restricted Endpoint"; their
  `api/v3` equivalents: 403 "Legacy Endpoint" (only for subscriptions before
  2025-08-31). `stable/dividends` works only for some symbols: KO (227 events
  from 1970), JNJ (228) and AAPL (92) return pay, record and declaration dates
  (pay date filled for 159, 160 and 92 events); O and BRK-B are refused as
  "Premium Query Parameter". `stable/dividends-calendar` with a date range:
  402 (the `from` value is premium). No rate-limit headers in any response, so
  the daily limit can only be read in the FMP dashboard.
- **P4b FMP calendar without a date range: fail for the story.** 1 call (12
  in total). 200, but only 44 symbols, all large well-known names (and ETFs
  such as SPY and VWO): the same sample of symbols the free plan allows.
- **P5 SEC company facts: pass with constraints.** `company_tickers.json`:
  10,429 rows, share classes with a dash (`BRK-B`). `companyfacts` is 3 to
  8 MB per company. For the 11 companies with filings, every figure has a
  concept in the latest 10-K, except where the sector does not report it:
  JPM and CB (bank, insurer) have no capital expenditure and no operating
  income, O (REIT) no operating income, CB no D&A, and NEE's capital
  expenditure is not under any of the four concepts tried. The concept varies
  by company: dividends paid is `PaymentsOfDividends` (AAPL, KO, PG, JPM),
  `PaymentsOfDividendsCommonStock` (MSFT, O, T, CB) or
  `PaymentsOfOrdinaryDividends` (JNJ); D&A has four concepts; a company can
  switch concept over the years (KO's `LongTermDebt` stops at FY2023,
  `LongTermDebtAndCapitalLeaseObligations` continues), so the mapping must
  take the concept with the latest fiscal year. `frames` (one concept, one
  year, all companies) is one 130 KB call covering 871 companies for
  `PaymentsOfDividends` CY2025. **XOM**: the ticker, and Wikipedia's CIK, now
  point to the new holding company ExxonMobil Holdings Corp (CIK 2115436),
  which has no 10-K yet; the history is under Exxon Mobil Corp (CIK 34088).
- **P6 Yahoo (`yfinance` 1.7.0): pass.** 503 tickers, no blocking and no
  errors. Bulk 1-year raw prices: 54 s, every ticker has data (251 trading
  days for 498). `Ticker.dividends`: 142 s, 420 payers, earliest 1962-01-16,
  median 121 events per payer. `Ticker.options`: 36 s, 502 with options (not
  NVR). Open interest on the next monthly expiry (2026-11-20) ranges from
  3,795 (BEN) to 139,028 (VZ). A bulk `yf.download(period="max",
  actions=True)` returns exactly the same dividend events as
  `Ticker.dividends` for KO, JNJ, O, BRK-B (none) and AAPL.
- **P6b Yahoo next pay date: pass.** `Ticker.calendar` for 503 tickers: 33 s,
  no errors; 420 have the next ex-dividend date and 413 the next pay date
  ("Dividend Date"). KO (ex 2026-12-01, pay 2026-12-15) and JNJ (ex 2026-11-24,
  pay 2026-12-08) match FMP exactly. It holds only the latest announced
  dividend (AAPL's shows August's).

## Decisions from the probes

- **S&P 500 list: Wikipedia.** FMP's list is paid. Wikipedia gives symbol,
  sector, sub-industry, date added and CIK in one page. CIK read as text.
- **Pay dates: Yahoo `Ticker.calendar`, collected weekly; estimated before
  that.** Each weekly run records the next announced ex-date and pay date, so
  real pay dates build up from the first load. Dividends paid before then get
  an estimated pay date (ex-date plus a number of days, per company once
  enough real ones are collected, otherwise the reference table's default).
- **FMP: dropped from version one.** Neither the list nor the dividend dates
  are on the free plan for the whole index. The `fmp` secret scope and the
  `bronze_fmp`, `bronze_fmp_publish`, `silver_landing_fmp` schemas are unused;
  removing them is a small iac change (task 3.4).
- **Yahoo: the main market source**, about 4 minutes a week for prices, full
  dividends, options and calendar. Prices and dividends can each be one bulk
  call.
- **SEC: `companyfacts` per company** (about 500 calls, under a minute at 10
  a second), keeping only the mapped concepts. The SEC change must handle:
  the concept chosen by latest fiscal year, sector gaps (banks and insurers
  without capital expenditure or operating income, so free cash flow and
  EBITDA are not computed for them), and a predecessor CIK for reorganised
  companies (XOM), kept in a small reference table.
- **Table budget.** About 15 source datasets (Wikipedia 1, SEC 2, Yahoo 4,
  RBA 2, FRED 1, purchases 1, reference about 4) at about 3 tables each (raw,
  publish, landing), plus about 7 in `silver_investments` and 6 in gold: about
  58 per environment, 116 for dev and prd. That fits the 200 to 230 left, with
  80 to 110 to spare.
