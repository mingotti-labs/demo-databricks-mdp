# airroi-market-summary-ingestion Specification

## Purpose
Ingests AirROI's short-term rental market data — a current snapshot
(`/markets/summary`) and a rolling forecast time series
(`/markets/metrics/all`) — for four confirmed real markets (Vitória da
Conquista/BA, Urubici/SC, Tauranga/NZ, Prado/BA with
`district="Cumuruxatiba"`) into `bronze_airroi`, modeled as SCD2 history in
`bronze_airroi_publish` — this project's first paid, authenticated API
source, requiring deliberate cost discipline throughout.

## Requirements

### Requirement: AirROI fetch helpers
`src/common/airroi.py` SHALL provide functions that perform an
authenticated HTTP POST against AirROI's `/markets/summary` and
`/markets/metrics/all` endpoints for a given `country`/`region`/`locality`
and optional `district`, sent as a nested `market` object (not flat
top-level fields — AirROI's own published example is incorrect for both
endpoints, confirmed via a real `422` response), using `X-API-KEY` header
auth with the key retrieved via `dbutils.secrets.get("airroi", "api_key")`,
and returning the parsed JSON response.

#### Scenario: Helpers work against the real API
- **WHEN** a helper is called with a real market's `country`, `region`,
  `locality` (display names, not URL slugs), and optional `district`
- **THEN** the call succeeds and returns the real response shape for that
  endpoint — not the field names shown in AirROI's own docs, confirmed
  wrong via real successful responses for both endpoints

#### Scenario: `district` genuinely filters, not silently ignored
- **WHEN** `fetch_market_summary` is called with `locality="Prado"` alone,
  versus with `locality="Prado"` + `district="Cumuruxatiba"`
- **THEN** the two calls return different `active_listings_count` values,
  proving `district` is honored by the API, not silently dropped

### Requirement: Fixed market list, same across all environments
`market_summary_raw` and `market_metrics_all_raw` SHALL each pull exactly
four markets — Vitória da Conquista/BA, Urubici/SC, Tauranga/NZ, and
Prado/BA with `district="Cumuruxatiba"` — identically in `dev`, `tst`, and
`prd`. No per-environment row-limiting or subsetting SHALL be applied,
since there is no free-tier or smaller-sample concept for this source.

#### Scenario: Same four markets in every environment
- **WHEN** the pipelines are deployed and run against `dev` or `prd`
- **THEN** `market_summary_raw` has exactly 4 rows and `market_metrics_all_raw`
  has exactly 48 rows (4 markets × ~12 months) in that environment,
  representing the same four markets

### Requirement: Full-refresh batch ingestion into bronze_airroi
`market_summary_raw` and `market_metrics_all_raw` SHALL each be a
Materialized View that re-fetches all four markets' current data on every
run — neither endpoint has an incremental cursor, so full-refresh batch
pull is the correct approach. Each row SHALL carry a platform-added
`ingested_timestamp` column (`current_timestamp()`, stamped inside the
dataset's own query).

#### Scenario: Pipeline run lands data with lineage timestamp
- **WHEN** either pipeline is run against a target
- **THEN** the corresponding `_raw` table exists, is populated with the
  expected row count, and every row has a non-null `ingested_timestamp`

### Requirement: SCD2 modeling only, no SCD1
`market_summary_scd2` and `market_metrics_all_scd2` SHALL exist in
`bronze_airroi_publish`, each built via `create_auto_cdc_from_snapshot_flow`
against a `@dp.temporary_view()` that wraps the corresponding `_raw` table
and adds a `transformed_timestamp` column. `market_summary_scd2` SHALL be
keyed by `_country`/`_region`/`_locality`/`_district`; `market_metrics_all_scd2`
SHALL additionally key by `date`. Neither key SHALL use the API's own
nested `market` map (Auto CDC's `keys=` needs flat columns, not a nested
struct/map type). Both `ingested_timestamp` and `transformed_timestamp`
SHALL be listed in `track_history_except_column_list`, so their per-run
difference does not itself trigger a spurious new history version. No SCD1
table SHALL be built for either pattern — a deliberate scope decision,
since SCD1 would be pure duplication of SCD2's `WHERE __END_AT IS NULL`
filter.

#### Scenario: SCD2 tables match source row count on initial load
- **WHEN** the SCD pipeline is run after both `_raw` tables are populated
- **THEN** `market_summary_scd2` has a row count matching
  `market_summary_raw` exactly (4 rows), and `market_metrics_all_scd2`
  matches `market_metrics_all_raw` exactly (48 rows)

#### Scenario: Re-running the pipeline does not create spurious history
- **WHEN** either raw pipeline is re-run with no real change in the
  underlying market data, and the SCD pipeline is re-run afterward
- **THEN** each SCD2 table's total row count (all versions, not just
  current) still equals its `_raw` table's row count — `ingested_timestamp`/
  `transformed_timestamp` differing between runs does NOT create new
  history versions on its own

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that both `_raw`
tables are populated with the expected row counts and expected columns
(including the platform timestamp columns), and that both `_scd2` tables'
row counts match their respective `_raw` tables, chained into one job
(`verify_airroi_market_summary_pattern`) so the pattern can be re-checked
on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_airroi_market_summary_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
