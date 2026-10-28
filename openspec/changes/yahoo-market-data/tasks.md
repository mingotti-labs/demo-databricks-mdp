## 1. Setting and probe

- [ ] 1.1 Add `benchmark_symbols` (`"SPY,NOBL"`) to `data/portfolio/settings.csv`
      and `reference_rows: 6` in `verification/bronze_checks/portfolio.yml`;
      `uv run python -m pytest` passes
- [x] 1.2 P1 (design): probe script `p8_yahoo_shapes.py` in
      `references/poc/dividend-portfolio/`, run on serverless with `run.py`;
      rows, keys, calendar fields and times recorded in design.md and the probes
      register; keys in D8 confirmed

## 2. Fetch

- [ ] 2.1 `tests/common/test_yahoo_market.py` for the helpers (symbol mapping,
      rows from small pandas frames, monthly expiry, JSON Lines) passes; ruff clean
- [ ] 2.2 `src/common/fetch_yahoo.py` (D1, D3, D4, D6); ruff clean

## 3. Pipelines and job

- [ ] 3.1 `src/layers/bronze/yahoo/` (four raw tables, D7) and
      `src/layers/bronze/yahoo_publish/` (four snapshot views and SCD2 flows,
      D8); ruff clean
- [ ] 3.2 `src/layers/silver/landing/yahoo/` (four Landing tables); ruff clean
- [ ] 3.3 `resources/pipelines/yahoo_market_data_ingestion.pipeline.yml`,
      `silver_landing_yahoo.pipeline.yml`, `resources/jobs/run_yahoo.job.yml`
      (fetch first, Python file task with the `yfinance` environment);
      `databricks bundle validate -t dev --profile DEFAULT` passes
- [ ] 3.4 `verification/bronze_checks/yahoo.yml` (`compare_latest_file_per: []`
      for all four), four entries in `verification/verify_silver_landing.py`,
      `yahoo` in `src/common/design_patterns.yml`; `uv run python -m pytest` passes

## 4. Verify in dev

- [ ] 4.1 Deploy to dev; run `run_portfolio`, then `run_yahoo` with
      `verify=true`: every task succeeds; record rows per layer and dataset,
      symbols skipped and task times in design.md
- [ ] 4.2 P2: run `run_yahoo` again; record new and closed versions per
      dataset
- [ ] 4.3 Check `BRK.B` (as `BRK-B`), a non-payer and both benchmarks in
      Landing
- [ ] 4.4 Stop the SQL warehouse after any query session

## 5. Registers and docs

- [ ] 5.1 `design-patterns.md`: `yahoo` in the "Used by" lines
- [ ] 5.2 `data-sources.md` `yahoo` entry; `source_systems/yahoo.md`, listed in
      its README
- [ ] 5.3 CLAUDE.md: "Sources" entry for Yahoo
