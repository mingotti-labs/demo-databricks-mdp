## 1. Probe and infrastructure

- [x] 1.1 Probe P7 from serverless: P4's two series requests (`1.10001.10.50.Q`,
      `1.10001.10.50.M`, CSV with labels), the row counts and the label columns. Put the
      script and its result in `references/poc/macro-prices/` and add a row to the probes
      register
- [x] 1.2 iac `abs-schemas-volume` applied: `bronze_abs`, `bronze_abs_publish` and
      `bronze_abs.s3_raw` exist in `mdp_dev` and `mdp_prd`, with the CI/CD grants

## 2. Fetch

- [x] 2.1 `src/common/abs_series.py`: `SERIES`, the request (a non-200 status or no
      rows fails with the key and the status), rows from the CSV (D1 columns, rows with
      no value skipped), `stamp`, `to_jsonl`. Unit tests on a trimmed CSV
- [x] 2.2 `src/common/fetch_abs.py` notebook: fetch every series, then write one dated
      JSON Lines file into `bronze_abs.s3_raw`
- [x] 2.3 Bundle variable `abs_api_url` in `cicd/databricks/free.yml` and
      `standard.yml`; regenerate `databricks.yml`

## 3. Pipelines and job

- [x] 3.1 `src/layers/bronze/abs/` (Auto Loader raw) and
      `src/layers/bronze/abs_publish/` (SCD1 snapshot Auto CDC by `series_key`, `time_period`)
- [x] 3.2 `src/layers/silver/landing/abs/` (`silver_landing.abs__observations`, no
      type change)
- [x] 3.3 Pipelines `bronze--abs--<target>` and `silver--abs--<target>`; job `run_abs`
      with `verify`
- [x] 3.4 `verification/bronze_checks/abs.yml` (`compare_latest_file_per`) and
      `verification/silver_landing_checks/abs.yml`
- [x] 3.5 Design pattern register entries for `abs`
- [x] 3.6 `uv run python -m pytest tests` passes; `databricks bundle validate`;
      `cicd/affected_units.py` selects `abs`

## 4. Verify in dev

- [x] 4.1 Re-read the table quota; stop and ask if it is above 488
- [ ] 4.2 Draft PR deploys to dev. `run_dev.py abs --param verify=true`: Landing holds 313
      quarterly rows (from 1948-Q3) and the monthly rows (from 2024-04), with the
      latest values matching the ABS
- [ ] 4.3 A second run: raw doubles; Publish and Landing write no row (counts and every
      `transformed_timestamp` unchanged)
- [ ] 4.4 Write the results into design.md

## 5. Docs

- [x] 5.1 CLAUDE.md "Sources": `abs`
- [x] 5.2 `references/docs/registers/data-sources.md` and a new `source_systems/abs.md`

## 6. Prd

- [ ] 6.1 Mark the PR ready. After the merge, CI runs `run_abs` in prd; check its counts
      against dev; then archive
