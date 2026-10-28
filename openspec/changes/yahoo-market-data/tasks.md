## 1. Benchmarks and probe

- [x] 1.1 `data/portfolio/benchmarks.csv` (D9), `benchmarks` in the portfolio
      raw `DATASETS`, its SCD2 and Landing tables, `verification/bronze_checks/portfolio.yml`
      (`reference_rows: 14`), the Silver Landing entry and `data/portfolio/README.md`;
      `uv run python -m pytest` passes
- [x] 1.2 P1 (design): probe script `p8_yahoo_shapes.py` in
      `references/poc/dividend-portfolio/`, run on serverless with `run.py`;
      rows, keys, calendar fields and times recorded in design.md and the probes
      register

## 2. Fetch

- [ ] 2.1 `tests/common/test_yahoo_market.py` for the helpers (symbol mapping,
      start date and reload rule, rows from small pandas frames, monthly expiry,
      JSON Lines) passes; ruff clean
- [ ] 2.2 `src/common/fetch_yahoo.py` notebook (D1, D3, D6, D7) with
      `fetch_state`; ruff clean
- [ ] 2.3 CLAUDE.md guardrails: the `%pip` exception for the Yahoo fetch
      notebook

## 3. Pipelines and job

- [ ] 3.1 `src/layers/bronze/yahoo/` (four raw tables) and
      `src/layers/bronze/yahoo_publish/` (three SCD1 and one SCD2 streaming
      flows, D8); ruff clean
- [ ] 3.2 `src/layers/silver/landing/yahoo/` (four Landing tables); ruff clean
- [ ] 3.3 `resources/pipelines/yahoo_market_data_ingestion.pipeline.yml`,
      `silver_landing_yahoo.pipeline.yml`, `resources/jobs/run_yahoo.job.yml`
      (fetch first, `reload_symbols` job parameter);
      `databricks bundle validate -t dev --profile DEFAULT` passes
- [ ] 3.4 `verification/bronze_checks/yahoo.yml`, four entries in
      `verification/verify_silver_landing.py`, `yahoo` in
      `src/common/design_patterns.yml`; `uv run python -m pytest` passes

## 4. Verify in dev

- [ ] 4.1 Deploy to dev; run `run_portfolio`, then `run_yahoo` with
      `verify=true`: every task succeeds; record rows per layer and dataset,
      symbols with no prices and task times in design.md
- [ ] 4.2 P2: second run (new days and event reloads only), a run with
      `reload_symbols` `AAPL`, a cancelled-and-repaired run; record results
- [ ] 4.3 Check `BRK.B` (as `BRK-B`), a non-payer, `^VIX` and a sector fund in
      Landing
- [ ] 4.4 Stop the SQL warehouse after any query session

## 5. Registers and docs

- [ ] 5.1 `design-patterns.md`: `yahoo` in the "Used by" lines
- [ ] 5.2 `data-sources.md` `yahoo` entry; `source_systems/yahoo.md`, listed in
      its README
- [ ] 5.3 CLAUDE.md: "Sources" entry for Yahoo
