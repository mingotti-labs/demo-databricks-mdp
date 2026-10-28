## Why

Step 4 of the dividend portfolio story (`demo-databricks-planning`, story design
revised 2026-10-25). The shortlist needs each company's fundamentals (net
income, cash flow, capital expenditure, debt, dividends paid ...), and SEC EDGAR
`companyfacts` gives them free for every S&P 500 company. It is also the first
source built on the raw shape agreed on 2026-10-28 (user): raw is append-only
and replayable (every fetch kept as a file and as rows), not a Materialized View
recomputed on each run.

## What Changes

- New source `sec`, run weekly by job `run_sec`:
  - A **fetch task** (first task of the job) reads the companies to fetch (the
    current Wikipedia CIKs plus the predecessor CIKs in `bronze_portfolio`) and
    the candidate concepts (the `portfolio` concept mapping), calls
    `company_tickers.json` and `companyfacts` per company with the
    `http_user_agent` contact and at most 10 requests per second, and writes
    dated files into the `bronze_sec.s3_raw` volume: company facts in long form
    for the candidate concepts only, and only for companies whose facts changed
    since their last file.
  - **Bronze raw**: `bronze_sec.company_tickers_raw` and
    `bronze_sec.company_facts_raw`, append-only streaming tables fed by Auto
    Loader from the volume, with a few warn expectations and `CLUSTER BY AUTO`.
  - **Bronze Publish**: `bronze_sec_publish.company_tickers_scd2` and
    `company_facts_scd2`, the bronze full pattern over the latest file of each
    company.
  - **Silver Landing**: `silver_landing_sec.company_tickers` and
    `company_facts` via `land_changes`.
- New design pattern `bronze_volume_append_autoloader_python` (fetch task writes
  dated files, Auto Loader appends) in the register; Yahoo reuses it next, and a
  later change moves Wikipedia and portfolio to it.
- Not in this change: choosing between concepts and picking the latest year
  (the `silver_investments` change); the Wikipedia and portfolio conversion.

## Cross-repo dependencies

Depends on a new `demo-databricks-iac` change (`raw-volumes-sec-yahoo-wikipedia`,
to be proposed): a `s3_raw` volume in `bronze_sec`, and in the same change
`bronze_yahoo` and `bronze_wikipedia` for the next steps, each with
`READ_VOLUME`/`WRITE_VOLUME` for the CI/CD service principal and the user, in
both deployments. It must be applied before this change is implemented. The
planned iac clean-up (remove the `fmp` scope and the `fmp` and `reference`
schemas) can ride in the same iac change.

## Model

Opus: the first use of a new raw pattern (append files plus Auto Loader feeding
a snapshot SCD2), with a probe to run before the code settles.

## Capabilities

### New Capabilities
- `sec-company-facts-ingestion`: fetch SEC tickers and company facts into
  append-only raw files and tables, SCD2 history, and Silver Landing.

### Modified Capabilities

## Impact

- New: `src/common/sec_edgar.py` (fetch and flatten helpers),
  `src/layers/bronze/sec/fetch.py` (notebook task), `src/layers/bronze/sec/`,
  `src/layers/bronze/sec_publish/`, `src/layers/silver/landing/sec/`, two
  pipelines, job `run_sec`, verification entries, unit tests.
- Reads across sources in the fetch task: `bronze_wikipedia_publish` and
  `bronze_portfolio_publish` (job-ordered, not a pipeline dependency).
- Tables: 6 new per target (2 raw, 2 SCD2, 2 Landing); metastore at about 301.
- External: about 505 SEC requests per weekly run, about one minute at the
  rate limit.
