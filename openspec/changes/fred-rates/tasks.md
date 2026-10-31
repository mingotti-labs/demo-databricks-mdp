## 0. Landing checks per source

- [x] 0.1 Dev baseline: run the `verify_silver_landing` job with an empty
      `source` before any change: 30 entities verified
- [x] 0.2 `src/common/silver_landing_checks.py`: load and validate one file or
      all of `verification/silver_landing_checks/`; unit tests, including that
      every source in `design_patterns.yml` with a `silver_landing` schema has a
      file
- [x] 0.3 The 13 files from the current `ENTITIES` list and
      `SOURCES_WITH_INGESTED_TIMESTAMP` (no entry changed); `verify_silver_landing.py`
      reads them and loses both constants
- [x] 0.4 Dev: the same job, empty `source`: 30 entities verified; one run with
      `source=yahoo` verifies 4

## 1. Probe

- [x] 1.1 Probe P1 from serverless (design.md): done 2026-10-31; scripts and
      result in `references/poc/fred-rates/`, row in the probes register
- [x] 1.2 iac `raw-volume-fred` applied: `bronze_fred.s3_raw` exists in
      `mdp_dev` and `mdp_prd`

## 2. Fetch

- [x] 2.1 `src/common/fred_series.py`: rows from the `series` and
      `series/observations` payloads (`.` skipped, real-time columns dropped,
      a missing key fails), the request start date; unit tests on trimmed
      payloads
- [x] 2.2 `src/common/fetch_fred.py` notebook: key from the secret scope, last
      stored date per series, `reload`, errors without the URL, one dated JSON
      Lines file into `bronze_fred.s3_raw`
- [x] 2.3 Bundle variable `fred_api_url` in `cicd/databricks/free.yml` and
      `standard.yml`; regenerate `databricks.yml`

## 3. Pipelines and job

- [x] 3.1 `src/layers/bronze/fred/` (Auto Loader raw) and
      `src/layers/bronze/fred_publish/` (SCD1 Auto CDC)
- [x] 3.2 `src/layers/silver/landing/fred/` (`silver_landing.fred__observations`,
      `observation_date` as DATE)
- [x] 3.3 Pipelines `bronze--fred--<target>`, `silver--fred--<target>`; job
      `run_fred` with `verify` and `reload`
- [x] 3.4 `verification/bronze_checks/fred.yml` and
      `verification/silver_landing_checks/fred.yml`
- [x] 3.5 Design pattern register entries for `fred`

## 4. Verify in dev

- [x] 4.1 Re-read the table quota; stop and ask if above 488
- [x] 4.2 Draft PR deploys to dev; `run_fred` as the service principal with
      `verify=true`: first run writes every observation; in
      `silver_landing.fred__observations` `DGS10` on 2026-10-29 is 4.98 and
      `DFEDTARU` / `DFEDTARL` on 2026-10-30 are 4 / 3.75
- [x] 4.3 Second run: requests only the last 31 days; Publish row count
      unchanged apart from new dates
- [x] 4.4 The `verify_silver_landing` job with an empty `source` verifies 31
      entities
- [x] 4.5 Results in design.md

## 5. Docs

- [x] 5.1 CLAUDE.md "Sources": `fred`
- [x] 5.2 `references/docs/registers/data-sources.md` and
      `source_systems/fred.md`
