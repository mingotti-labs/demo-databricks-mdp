## 1. Probe

- [x] 1.1 Probe P1 from serverless (design.md): done 2026-10-31; scripts and
      result in `references/poc/fred-rates/`, row in the probes register
- [ ] 1.2 iac `raw-volume-fred` applied: `bronze_fred.s3_raw` exists in
      `mdp_dev` and `mdp_prd`

## 2. Fetch

- [ ] 2.1 `src/common/fred_series.py`: rows from the `series` and
      `series/observations` payloads (`.` skipped, real-time columns dropped,
      a missing key fails), the request start date; unit tests on trimmed
      payloads
- [ ] 2.2 `src/common/fetch_fred.py` notebook: key from the secret scope, last
      stored date per series, `reload`, errors without the URL, one dated JSON
      Lines file into `bronze_fred.s3_raw`
- [ ] 2.3 Bundle variable `fred_api_url` in `cicd/databricks/free.yml` and
      `standard.yml`; regenerate `databricks.yml`

## 3. Pipelines and job

- [ ] 3.1 `src/layers/bronze/fred/` (Auto Loader raw) and
      `src/layers/bronze/fred_publish/` (SCD1 Auto CDC)
- [ ] 3.2 `src/layers/silver/landing/fred/` (`silver_landing.fred__observations`,
      `observation_date` as DATE)
- [ ] 3.3 Pipelines `bronze--fred--<target>`, `silver--fred--<target>`; job
      `run_fred` with `verify` and `reload`
- [ ] 3.4 `verification/bronze_checks/fred.yml` and the Silver Landing entry
- [ ] 3.5 Design pattern register entries for `fred`

## 4. Verify in dev

- [ ] 4.1 Re-read the table quota; stop and ask if above 488
- [ ] 4.2 Draft PR deploys to dev; `run_fred` as the service principal with
      `verify=true`: first run writes every observation; `DGS10` on 2026-10-29
      is 4.98 in `silver_landing.fred__observations`
- [ ] 4.3 Second run: requests only the last 31 days; Publish row count
      unchanged apart from new dates
- [ ] 4.4 Results in design.md

## 5. Docs

- [ ] 5.1 CLAUDE.md "Sources": `fred`
- [ ] 5.2 `references/docs/registers/data-sources.md` and
      `source_systems/fred.md`
