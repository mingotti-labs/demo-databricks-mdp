## 1. Settings files

- [x] 1.1 `data/portfolio/{concept_mapping,predecessor_ciks,settings,risk_levels,target_mix}.csv`
      with the starting values in design D6, and a short `data/portfolio/README.md`
      (what each file is, the key, "the repo is the master, the volume is
      overwritten")
- [x] 1.2 `tests/common/test_portfolio_settings.py`: each file parses, has the
      columns in D5 and no duplicate key; `uv run python -m pytest` passes

## 2. Copy step, pipelines and job

- [x] 2.1 `src/common/copy_repo_files.py` (notebook: copy the files a glob names to the
      volume path, overwrite); ruff clean
- [x] 2.2 `src/layers/bronze/portfolio/` (five `<dataset>_raw` Materialized Views)
      and `src/layers/bronze/portfolio_publish/` (five SCD2 flows); ruff clean
- [x] 2.3 `src/layers/silver/landing/portfolio/` (five Landing tables); ruff clean
- [x] 2.4 `resources/pipelines/portfolio_settings_ingestion.pipeline.yml`,
      `silver_landing_portfolio.pipeline.yml`, `resources/jobs/run_portfolio.job.yml`
      (copy first)
- [x] 2.5 `verification/bronze_checks/portfolio.yml`, five entries in
      `verification/verify_silver_landing.py`, `portfolio` in
      `src/common/design_patterns.yml`
- [x] 2.6 Test in `tests/cicd/` that a change to a `data/portfolio/` CSV selects
      the `portfolio` unit (design D3); `uv run python -m pytest` passes
- [x] 2.7 `databricks bundle validate -t dev` passes

## 3. Verify in dev

- [x] 3.1 Deploy to dev; run `run_portfolio` with `verify=true`; every task
      succeeds; the five volume files match the repo; record counts in design.md
- [x] 3.2 Change one value in `settings.csv`, deploy, run: exactly one version
      closed and one inserted in `settings_scd2`, no new version elsewhere;
      revert the value, deploy, run (record the counts)
- [x] 3.3 Stop the SQL warehouse after any query session (Free Edition pool)

## 4. Registers and docs

- [x] 4.1 `design-patterns.md`: new `bronze_volume_csv_materialized_view_python`;
      add portfolio and wikipedia to the "Used by" lines of the patterns they use
- [x] 4.2 `data-sources.md`: `wikipedia` and `portfolio` entries;
      `source_systems/wikipedia.md` and `source_systems/portfolio.md`, listed in
      `source_systems/README.md`
- [x] 4.3 CLAUDE.md: `data/` in the repository structure, a "Sources" entry for
      portfolio
