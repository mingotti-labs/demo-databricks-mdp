## Why

The dividend portfolio story needs settings we curate ourselves: the SEC concept
mapping, the list of predecessor CIKs (ExxonMobil's new holding company has no
10-K yet), the risk-level thresholds, the target mix and limits, the withholding
rate and the default pay-date offset. The user decided (story design, revised
2026-10-25) that all company-owned data lives in one source, `portfolio`, as CSV
files in the `bronze_portfolio.s3_raw` volume, with the master copies committed
in this repo. The SEC change needs the predecessor list, so this comes first.

## What Changes

- Five CSV files committed under `data/portfolio/`: `concept_mapping`,
  `predecessor_ciks`, `settings`, `risk_levels`, `target_mix`, with starting
  values from the story design and the SEC probe.
- A run-job step copies them into
  `/Volumes/<catalog>/bronze_portfolio/s3_raw/<dataset>/landing/<dataset>.csv`
  on every run (dev and prd), so the volume always matches `main`.
- Bronze: one Materialized View per file in `bronze_portfolio` (`<dataset>_raw`,
  text values, `ingested_timestamp`), SCD2 per file in `bronze_portfolio_publish`
  (the bronze full pattern), so every change to a setting is kept with its date.
- Silver Landing per file in `silver_landing_portfolio` (change feed).
- Pipelines `bronze--portfolio--<target>` and `silver--portfolio--<target>`, job
  `run--portfolio--<target>` with the `verify` parameter, verification spec and
  Silver Landing entries, design pattern register entries.
- New design pattern `bronze_volume_csv_materialized_view_python` (a CSV kept in
  the repo, copied to a volume, read by a Materialized View).
- Fix from `wikipedia-sp500-ingestion`: add Wikipedia to `data-sources.md`, to the
  "Used by" lines of `design-patterns.md` and a `source_systems/wikipedia.md`
  page, which that change missed.
- The purchases CSV is not part of this change (story step 11); real purchases
  will never be committed, so the copy step only copies the listed settings.

## Capabilities

### New Capabilities

- `portfolio-internal-data`: the curated settings as committed CSVs, copied to
  the volume, landed with SCD2 history and Silver Landing.

### Modified Capabilities

None.

## Impact

- New: `data/portfolio/*.csv`, `src/common/copy_repo_files.py` (notebook),
  `src/layers/bronze/portfolio/`, `src/layers/bronze/portfolio_publish/`,
  `src/layers/silver/landing/portfolio/`, two pipelines, one job,
  `verification/bronze_checks/portfolio.yml`.
- Changed: `verification/verify_silver_landing.py`,
  `src/common/design_patterns.yml`, registers, `CLAUDE.md`.
- Tables per environment: 15 (5 raw, 5 SCD2, 5 Landing), 30 for dev and prd.
- Volume writes by the CI/CD service principal (it has `WRITE_VOLUME`).

## Cross-repo dependencies

Depends on `dividend-portfolio-schemas` in `demo-databricks-iac` (applied,
archived): the `bronze_portfolio`, `bronze_portfolio_publish` and
`silver_landing_portfolio` schemas, the `s3_raw` volume and its grants. Later, a
small iac change removes the unused `fmp` scope and the `fmp` and `reference`
schemas (story design, step 6).

## Model

Sonnet: the shape repeats the iso source, with a copy step in front; the new
parts (volume copy, CSV reader) are small.
