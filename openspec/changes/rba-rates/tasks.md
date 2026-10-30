## 1. Probe

- [x] 1.1 iac `raw-volume-rba` applied: `bronze_rba.s3_raw` exists in
      `mdp_dev` and `mdp_prd`
- [x] 1.2 `src/common/rba_tables.py`: parse a file into long rows (header
      rows, byte order mark, empty cells skipped); unit tests on a trimmed copy
      of each file in `tests/`
- [x] 1.3 Probe P1 from serverless (design.md); scripts and result in
      `references/poc/rba-rates/`, row in the probes register

## 2. Fetch

- [x] 2.1 `rba_tables.py`: rows from a cut-off date (31 days before the last
      stored date), unit tested
- [x] 2.2 `src/common/fetch_rba.py` notebook: last stored date per table,
      `reload`, one dated JSON Lines file per table into `bronze_rba.s3_raw`
- [x] 2.3 Bundle variable `rba_tables_url` in `cicd/databricks/free.yml` and
      `standard.yml`; regenerate `databricks.yml`

## 3. Pipelines and job

- [x] 3.1 `src/layers/bronze/rba/observations_raw.py` (Auto Loader) and
      `src/layers/bronze/rba_publish/observations.py` (SCD1 Auto CDC)
- [x] 3.2 `src/layers/silver/landing/rba/observations.py`
      (`silver_landing.rba__observations`)
- [x] 3.3 Pipelines `bronze--rba--<target>`, `silver--rba--<target>`; job
      `run_rba` with `verify` and `reload`
- [x] 3.4 `verification/bronze_checks/rba.yml` and the Silver Landing entry
- [x] 3.5 Design pattern register entries for `rba`

## 4. Verify in dev

- [ ] 4.1 Re-read the table quota; stop and ask if above 488
- [ ] 4.2 Draft PR deploys to dev; `run_rba` as the service principal with
      `verify=true`: first run writes every row; `FXRUSD`, `FIRMMCRTD`,
      `FCMYGBAG10D` and `FILRHLBVS` are in `silver_landing.rba__observations`
- [ ] 4.3 Second run: writes only the last 31 days per table; Publish row
      count unchanged apart from new dates
- [ ] 4.4 Results in design.md

## 5. Docs

- [ ] 5.1 CLAUDE.md "Sources": `rba`
- [ ] 5.2 `references/docs/registers/data-sources.md` and
      `source_systems/rba.md`
