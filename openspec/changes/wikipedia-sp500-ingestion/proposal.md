## Why

The dividend portfolio story needs the S&P 500 list. The probes
(`dividend-portfolio-probes`, P3 and P4) showed FMP's free plan refuses it and
Wikipedia's "List of S&P 500 companies" gives symbol, sector, GICS sub-industry,
date added and CIK in one parseable table. This is the first source of the story
and the one every later source joins to.

## What Changes

- New source `wikipedia`: a Python pull of the constituents table into
  `bronze_wikipedia.sp500_constituents_raw` (Materialized View, full refresh),
  SCD2 in `bronze_wikipedia_publish.sp500_constituents_scd2` (the bronze full
  pattern), and `silver_landing_wikipedia.sp500_constituents` (change-feed
  Landing).
- SCD2 versions are the index membership history: a company leaving the index
  closes its version, a new one opens a version, so joins and exits can be
  shown from the first load.
- New pipelines `bronze--wikipedia--<target>` and `silver--wikipedia--<target>`,
  job `run--wikipedia--<target>` with the `verify` parameter, a verification spec
  `verification/bronze_checks/wikipedia.yml` and a Silver Landing entry.
- Bundle variables `wikipedia_sp500_url` and `http_user_agent` (contact
  string for public sites; the SEC change reuses it), in both edition files and
  the regenerated `databricks.yml`.
- Design pattern register entries for the three schemas.
- No Silver Normalised (decided per source in the story design: 500 rows of one
  entity, nothing to restructure). No iac change: the three schemas exist.

## Capabilities

### New Capabilities

- `wikipedia-sp500-ingestion`: fetch, parse and land the S&P 500 constituents
  table; SCD2 membership history; Silver Landing; verification.

### Modified Capabilities

None.

## Impact

- Code: `src/common/wikipedia_sp500.py`, `src/layers/bronze/wikipedia/`,
  `src/layers/bronze/wikipedia_publish/`, `src/layers/silver/landing/wikipedia/`,
  `resources/pipelines/` (2), `resources/jobs/run_wikipedia.job.yml`,
  `verification/`, `src/common/design_patterns.yml`, `cicd/databricks/*.yml`,
  `databricks.yml` (generated), `tests/common/`, `CLAUDE.md`.
- Tables per environment: 3 (of the story's budget of about 116 in total).
- Network: one GET of `en.wikipedia.org` per weekly run.

## Cross-repo dependencies

Depends on `dividend-portfolio-schemas` in `demo-databricks-iac` (applied,
archived): `bronze_wikipedia`, `bronze_wikipedia_publish` and
`silver_landing_wikipedia` and their grants for the CI/CD service principal.

## Model

Sonnet: the shape repeats the iso and geonames sources (single fetch helper,
Materialized View, bronze full pattern, change-feed Landing).
