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
  environment listing its PyPI packages), kept in a scratch workspace folder
  `/Workspace/Users/<user>/probes/dividend-portfolio/`. Local copies sit in the
  session scratchpad, not the repo. This is the real shape (serverless, packages
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

None: nothing is deployed. After the results are recorded, the scratch
workspace folder is deleted (with the user's approval) and the one-time runs are
left in the job run history.
