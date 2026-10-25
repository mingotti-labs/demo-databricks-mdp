## 1. Fetch helper

- [x] 1.1 `src/common/wikipedia_sp500.py` with the parse in design D1; a pytest
      in `tests/common/` on a small saved HTML fragment (columns, CIK padding,
      text values) passes with `uv run pytest tests/common`
- [x] 1.2 (run locally: same public page; serverless is proven by the pipeline run in 3.1) Against the real page: rows at
      least 480, every CIK 10 digits, `symbol` distinct; record the numbers in
      this design.md

## 2. Pipelines and job

- [x] 2.1 `src/layers/bronze/wikipedia/sp500_constituents_raw.py` (Materialized
      View, `ingested_timestamp`, CC BY-SA attribution comment) and
      `src/layers/bronze/wikipedia_publish/sp500_constituents_scd2.py`; ruff
      clean
- [x] 2.2 `src/layers/silver/landing/wikipedia/sp500_constituents.py` with
      `land_changes`; ruff clean
- [x] 2.3 `resources/pipelines/wikipedia_sp500_ingestion.pipeline.yml`,
      `silver_landing_wikipedia.pipeline.yml`,
      `resources/jobs/run_wikipedia.job.yml`; variables in
      `cicd/databricks/free.yml` and `standard.yml`; `uv run python
      cicd/apply_edition.py` then `--check` passes
- [x] 2.4 `verification/bronze_checks/wikipedia.yml`, Silver Landing entry in
      `verification/verify_silver_landing.py`, `wikipedia` entries in
      `src/common/design_patterns.yml`; `uv run pytest` passes
- [x] 2.5 `databricks bundle validate -t dev` passes

## 3. Verify in dev

- [x] 3.1 Deploy to dev; run `run_wikipedia` with `verify=true`; every task
      succeeds; record row counts in design.md
- [x] 3.2 Check the tables: raw at least 480 rows, current SCD2 versions equal
      raw, Landing current rows equal SCD2 current rows, tags on the three
      schemas
- [x] 3.3 Run again with no change: no SCD2 version inserted or closed (compare
      version counts before and after)

## 4. Docs

- [x] 4.1 CLAUDE.md "Sources" entry for Wikipedia (what it holds, symbol key,
      history from first load, XOM-style CIK issues belong to the SEC change);
      add a probes-register line only if a probe was run
