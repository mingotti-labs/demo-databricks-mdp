## 1. Bundle configuration

- [x] 1.1 Added `airroi_base_url` variable to `databricks.yml` (fixed
      across targets: `https://api.airroi.com`, confirmed via AirROI's
      own getting-started docs). Market list kept as a plain Python
      constant in each pipeline file, not a bundle variable — a fixed
      4-market list has no dev/tst/prd variation to parameterize

## 2. Fetch helper

- [x] 2.1 Created `src/common/airroi.py` with `fetch_market_summary(...)`
      — HTTP POST to `/markets/summary`, `X-API-KEY` header auth
- [x] 2.2 Verified `fetch_market_summary` against the real AirROI API —
      **two real corrections found, not caught by pre-flight docs
      review**: request shape (nested `market` object, not flat fields,
      confirmed via a real `422`) and response field names (real:
      `active_listings_count`/`average_daily_rate`/`occupancy`/`rev_par`/
      `revenue`/`booking_lead_time`/`length_of_stay`/`min_nights`, none
      matching AirROI's docs)
- [x] 2.3 Added `fetch_market_metrics_all(...)` — HTTP POST to
      `/markets/metrics/all`, same request shape/auth as
      `fetch_market_summary`
- [x] 2.4 Verified `fetch_market_metrics_all` against the real API (one
      test call, Urubici) — real response is `{market, results}`, each
      `results` entry a `{date, <7 metrics as distribution objects>,
      active_listings_count}` shape, ~12 rows (rolling monthly window)

## 3. Raw ingestion pipelines

- [x] 3.1 Created `src/layers/bronze/airroi/market_summary_raw.py` — a
      Materialized View looping over four markets (display names:
      Brazil/Bahia/Vitória da Conquista, Brazil/Santa Catarina/Urubici,
      New Zealand/Bay of Plenty/Tauranga, Brazil/Bahia/Prado with
      `district="Cumuruxatiba"`), tagging each row with flat
      `_country`/`_region`/`_locality`/`_district` columns plus
      `ingested_timestamp`
- [x] 3.2 Created `src/layers/bronze/airroi/market_metrics_all_raw.py` —
      same 4 markets, one row per `(market, date)`, metric structs kept
      as-is, plus `ingested_timestamp`
- [x] 3.3 Created `resources/pipelines/airroi_market_summary_ingestion.pipeline.yml`
      (globs the whole `bronze/airroi/` directory — both raw pipelines
      run together)
- [x] 3.4 `databricks bundle validate` passed for dev
- [x] 3.5 Deployed and ran against `dev` — `market_summary_raw`: 4 rows,
      one per market, zero nulls in any required column;
      `market_metrics_all_raw`: 48 rows (4 markets × 12 months), confirmed
      via `discover-schema`/direct query, not just pipeline success status

## 4. SCD2 modeling pipelines (SCD2 only, no SCD1)

- [x] 4.1 Created `src/layers/bronze/airroi_publish/market_summary_scd2.py`
      — `create_auto_cdc_from_snapshot_flow` via a `@dp.temporary_view()`
      that stamps `transformed_timestamp` on `bronze_airroi.market_summary_raw`,
      keyed by `_country`/`_region`/`_locality`/`_district`,
      `track_history_except_column_list=["ingested_timestamp",
      "transformed_timestamp"]`
- [x] 4.2 Created `src/layers/bronze/airroi_publish/market_metrics_all_scd2.py`
      — same pattern, keyed by `_country`/`_region`/`_locality`/`_district`/
      `date`
- [x] 4.3 Created `resources/pipelines/airroi_market_summary_scd_modeling.pipeline.yml`
      (globs the whole `bronze/airroi_publish/` directory — both SCD
      pipelines run together)
- [x] 4.4 Deployed and ran against `dev` — `market_summary_scd2`: 4
      current rows (`WHERE __END_AT IS NULL`), 4 total rows;
      `market_metrics_all_scd2`: 48 current rows, 48 total rows. Total ==
      current in both confirms `track_history_except_column_list` actually
      prevented spurious versioning across multiple runs today, not just
      on paper

## 5. Verification suite

- [x] 5.1 Updated `verification/verify_airroi_market_summary_ingestion.py`
      for 4 markets + `_district`/`ingested_timestamp` columns
- [x] 5.2 Updated `verification/verify_airroi_market_summary_scd.py`'s
      header comment to reflect the timestamp-exclusion proof
- [x] 5.3 Created `verification/verify_airroi_market_metrics_all_ingestion.py`
      (expects 48 rows, distribution-struct columns present)
- [x] 5.4 Created `verification/verify_airroi_market_metrics_all_scd.py`
- [x] 5.5 Added both new tasks to `resources/jobs/verify_airroi_market_summary_pattern.job.yml`
- [x] 5.6 Ran the full verification job against `dev` — all four tasks
      `SUCCESS`

## 6. Documentation

- [x] 6.1 Added/updated a "Sources" entry in CLAUDE.md for AirROI covering
      both endpoints, all four markets, the Cumuruxatiba/`district`
      finding, the timestamp columns, and the paid-API cost discipline
- [x] 6.2 Updated CLAUDE.md's repository-structure tree for
      `bronze/airroi/` and `bronze/airroi_publish/`
- [x] 6.3 Documented the `ingested_timestamp`/`transformed_timestamp`
      convention in NAMING.md ("Platform-added timestamp columns")
- [x] 6.4 Created `docs/source_systems/` — one file per source system
      (`airroi.md`, `acnc.md`, `nsw_spatial.md`, `ungm.md`, `neon.md`,
      `clickstream.md`, plus a `README.md` index). `airroi.md` includes a
      metrics glossary (`rev_par`/`revpar`, `revenue`, `occupancy`, etc.)

## 7. Rollout to tst/prd

- [x] 7.1 Merged to `main` via PR #26, triggering CI/CD deploy to `tst`
      (automatic) and `prd` (manual approval gate, approved)
- [x] 7.2 Triggered a real pipeline run in `prd` — first attempt failed on
      `dbutils.secrets.get("airroi", "api_key")` under the CI/CD SP (see
      `demo-databricks-iac`'s `phase3h-airroi-cicd-secret-grant`: the
      `airroi` secret scope had no CI/CD SP grant at all, since AirROI is
      the first source reading a secret scope directly rather than via a
      UC Connection). Fixed with a `databricks_secret_acl` grant, re-ran:
      both raw pipelines `COMPLETED` (4 markets, 48 metric rows), both SCD
      pipelines `COMPLETED` (4/48 rows matching raw exactly), verification
      job all 4 tasks `SUCCESS` — confirmed via direct queries, not just
      pipeline status
- [x] 7.3 `tst` received the deployed code but was not separately run with
      real API calls — same configuration as `dev`, would duplicate cost
      without proving anything new (see design.md's Migration Plan)
