## 1. Bundle configuration

- [x] 1.1 Added `ungm_base_url` variable to `databricks.yml`, overridden per
      target: `dev`/`tst` → `https://wwwtest3.ungm.org`, `prd` →
      `https://www.ungm.org`

## 2. Fetch helper

- [x] 2.1 Created `src/common/ungm.py` with `fetch_ungm_endpoint(base_url,
      path, auth_token=None)` — HTTP GET, returns parsed JSON records;
      `auth_token` unused but passed through as a bearer header if ever
      provided; comment documents the `dbutils.secrets.get("ungm",
      "api_token")` retrieval a future authenticated endpoint would use
- [x] 2.2 Verified the helper against both real endpoints directly (curl,
      then Python `requests`) — found and fixed a real issue: UNGM's WAF
      blocks `requests`' default User-Agent with a 403 (reproducible even
      locally, identical URL: curl's UA gets 200, `python-requests`' UA
      gets 403). Fixed by setting an explicit `User-Agent` header

## 3. Raw ingestion pipeline

- [x] 3.1 Created `src/layers/bronze/ungm/unspsc_public_raw.py` — a
      Materialized View calling the fetch helper, `requests` declared as an
      explicit pipeline environment dependency
- [x] 3.2 Created `resources/pipelines/ungm_unspsc_ingestion.pipeline.yml`
- [x] 3.3 `databricks bundle validate` passed for dev/tst/prd
- [x] 3.4 First deploy+run attempt failed twice before succeeding, each a
      real, fixed issue: (a) `UNSUPPORTED_LIBRARY_FILE_TYPE` on
      `src/common/.gitkeep` — removed the now-unneeded marker file; (b)
      `ModuleNotFoundError: No module named 'common'` — glob-including
      `src/common/**` in `libraries` does NOT add it to `sys.path`; fixed
      with `sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")`,
      threading DAB's `${workspace.file_path}` through the pipeline's
      `configuration` block (the same variable the documented `--editable`
      shared-package pattern relies on, used directly since this repo has
      no setuptools/package-discovery config yet). Third attempt
      `COMPLETED`: `unspsc_public_raw` populated with 12,721 rows (test
      endpoint), correct `Id`/`ParentId`/`UNSPSCode`/`Title` shape

## 4. SCD modeling pipeline

- [x] 4.1 Created `src/layers/bronze/ungm_publish/unspsc_public_snapshot.py`
      (materialized-view batch snapshot of `bronze_ungm.unspsc_public_raw`)
- [x] 4.2 Created `unspsc_public_scd1.py` and `unspsc_public_scd2.py` —
      `create_auto_cdc_from_snapshot_flow`, keyed by `Id`
- [x] 4.3 Created `resources/pipelines/ungm_unspsc_scd_modeling.pipeline.yml`
- [x] 4.4 Deployed and ran against `dev` — `COMPLETED` on first attempt;
      `unspsc_public_scd1`/`unspsc_public_scd2` row counts match
      `unspsc_public_raw` exactly (12,721 each)

## 5. Verification suite

- [x] 5.1 Created `verification/verify_unspsc_ingestion.py`
- [x] 5.2 Created `verification/verify_unspsc_scd.py`
- [x] 5.3 Created `resources/jobs/verify_unspsc_pattern.job.yml`
- [x] 5.4 Ran against `dev` — both tasks `SUCCESS`

## 6. Documentation

- [x] 6.1 Added a "Sources" entry to CLAUDE.md for UNGM/UNSPSC covering the
      pattern, endpoint-per-target split, auth placeholder, the
      `src/common` import mechanism (with the real failure/fix), the WAF
      User-Agent gotcha, and the Python-only SCD scope decision
- [x] 6.2 Added a `<data_source>_public` naming note to NAMING.md
- [x] 6.3 Added `bronze/ungm/` and `bronze/ungm_publish/` to CLAUDE.md's
      repository-structure tree, and corrected the `src/common/` tree
      comment (not actually wheel-packaged, confirmed mechanism is
      sys.path-based)
