## 1. Bundle configuration

- [x] 1.1 Added `airroi_base_url` variable to `databricks.yml` (fixed
      across targets: `https://api.airroi.com`, confirmed via AirROI's
      own getting-started docs). Markets list kept as a plain Python
      constant in the pipeline file, not a bundle variable — a fixed
      3-market list has no dev/tst/prd variation to parameterize

## 2. Fetch helper

- [x] 2.1 Created `src/common/airroi.py` with
      `fetch_market_summary(base_url, api_key, country, region, locality)`
      — HTTP POST to `/markets/summary`, `X-API-KEY` header auth
- [x] 2.2 Verified against the real AirROI API — **two real corrections
      found, not caught by pre-flight docs review**:
      - First real call: `422` — AirROI's own published request example
        (`{"country_code", "state", "city"}` flat fields) is wrong for
        this endpoint; the real shape is a nested `market` object
        (`{"market": {"country", "region", "locality"}}`), confirmed via
        the `422` error body itself. Fixed and improved error handling to
        surface the response body (it wasn't visible before, since
        `raise_for_status()` doesn't include it)
      - Second real call (after the fix): succeeded, but response field
        names also don't match AirROI's docs — real fields are
        `active_listings_count`, `average_daily_rate`, `occupancy`,
        `rev_par`, `revenue`, `booking_lead_time`, `length_of_stay`,
        `min_nights`, and a structured `market` map, not the documented
        `active_listings`/`average_adr`/`average_occupancy`/etc. No
        `currency` field is returned at all (presumed USD, not confirmed)
      - Total cost: 2 failed 1-call attempts (fail-fast loop stopped at
        the first market each time) + 1 successful 3-call run ≈ 5 calls

## 3. Raw ingestion pipeline

- [x] 3.1 Created `src/layers/bronze/airroi/market_summary_raw.py` — a
      Materialized View looping over the three markets (display names:
      Brazil/Bahia/Vitória da Conquista, Brazil/Santa Catarina/Urubici,
      New Zealand/Bay of Plenty/Tauranga — not URL slugs), calling the
      fetch helper once per market, unioning results into one DataFrame,
      tagging each row with flat `_country`/`_region`/`_locality` columns
- [x] 3.2 Created `resources/pipelines/airroi_market_summary_ingestion.pipeline.yml`
- [x] 3.3 `databricks bundle validate` passed for dev
- [x] 3.4 Deployed and ran against `dev` — `COMPLETED` on the second real
      attempt (after the request-shape fix); `market_summary_raw`
      populated with exactly 3 rows, zero nulls across every column,
      confirmed via `discover-schema`

## 4. SCD2 modeling pipeline (SCD2 only, no SCD1)

- [x] 4.1 Created `src/layers/bronze/airroi_publish/market_summary_scd2.py`
      — `create_auto_cdc_from_snapshot_flow` against
      `bronze_airroi.market_summary_raw` directly, keyed by the flat
      `_country`/`_region`/`_locality` columns (not the `market` map --
      Auto CDC's `keys=` needs flat columns, not a nested struct/map type)
- [x] 4.2 Created `resources/pipelines/airroi_market_summary_scd_modeling.pipeline.yml`
- [x] 4.3 Deployed and ran against `dev` — `COMPLETED` on first attempt
      (no API calls needed, reads from the already-landed raw table);
      `market_summary_scd2` row count confirmed matching
      `market_summary_raw` exactly (3/3)

## 5. Verification suite

- [x] 5.1 Created `verification/verify_airroi_market_summary_ingestion.py`
- [x] 5.2 Created `verification/verify_airroi_market_summary_scd.py`
- [x] 5.3 Created `resources/jobs/verify_airroi_market_summary_pattern.job.yml`
- [x] 5.4 Ran against `dev` — both tasks `SUCCESS` (free to run, only
      queries already-landed Delta tables, no AirROI API calls)

## 6. Documentation

- [x] 6.1 Added a "Sources" entry to CLAUDE.md for AirROI covering the
      fetch-helper design, the paid-API cost discipline (including the
      real $0.10/call rate vs. the advertised $0.01), the markets
      confirmed/dropped during scoping (with reasoning), the SCD2-only
      decision, the request/response shape corrections, the flat-key
      choice, and the unconfirmed `revenue` time period
- [x] 6.2 Added `bronze/airroi/` and `bronze/airroi_publish/` to
      CLAUDE.md's repository-structure tree
