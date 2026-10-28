## 0. Prerequisite

- [ ] 0.1 The iac change with `bronze_sec.s3_raw` (and grants) is merged and
      applied; `databricks volumes read mdp_dev.bronze_sec.s3_raw --profile DEFAULT`
      returns the volume

## 1. Probes

- [ ] 1.1 P1 (design): probe script in `references/poc/dividend-portfolio/`,
      run on serverless with `run.py`; record rows per company, null and
      duplicate keys, and the extrapolated size in design.md and the probes
      register; settle the D8 facts key
- [ ] 1.2 P2 (design): confirm automatic clustering from Python in a pipeline
      on Free Edition; record the result

## 2. Fetch

- [ ] 2.1 `src/common/sec_edgar.py`: fetch with rate limit and `User-Agent`,
      flatten facts to long form for the mapped concepts, reshape tickers,
      content hash, file names; `tests/common/test_sec_edgar.py` with small
      fixtures passes (`uv run python -m pytest`); ruff clean
- [ ] 2.2 `src/common/fetch_sec.py` notebook (D4, D5, D6): reads the inputs,
      writes changed files only; ruff clean

## 3. Pipelines and job

- [ ] 3.1 `src/layers/bronze/sec/` (two Auto Loader raw tables, D7) and
      `src/layers/bronze/sec_publish/` (two snapshot views and SCD2 flows, D8);
      ruff clean
- [ ] 3.2 `src/layers/silver/landing/sec/` (two Landing tables); ruff clean
- [ ] 3.3 `resources/pipelines/sec_company_facts_ingestion.pipeline.yml`,
      `silver_landing_sec.pipeline.yml`, `resources/jobs/run_sec.job.yml`
      (fetch first); `databricks bundle validate -t dev --profile DEFAULT` passes
- [ ] 3.4 `compare_latest_file_per` option in `src/common/bronze_checks.py` (D10) with unit
      tests; `verification/bronze_checks/sec.yml`; two entries in
      `verification/verify_silver_landing.py`; `sec` in
      `src/common/design_patterns.yml`; `uv run python -m pytest` passes

## 4. Verify in dev

- [ ] 4.1 Deploy to dev; run `run_sec` with `verify=true`: every task succeeds;
      record files written, raw rows, SCD2 current rows and Landing rows per
      table, and the fetch time, in design.md
- [ ] 4.2 Run `run_sec` again: record files written (expected none or a few) and
      SCD2 versions added (expected none, or only for companies that filed)
- [ ] 4.3 Check XOM: facts under `0000034088` are present; the 404s logged by the
      fetch are listed in design.md
- [ ] 4.4 Stop the SQL warehouse after any query session

## 5. Registers and docs

- [ ] 5.1 `design-patterns.md`: new `bronze_volume_append_autoloader_python`;
      `sec` added to the "Used by" lines of the patterns it uses
- [ ] 5.2 `data-sources.md` `sec` entry; `source_systems/sec.md` (endpoints,
      `User-Agent`, rate, long-form reshape, 404s), listed in its README
- [ ] 5.3 CLAUDE.md: "Sources" entry for SEC
