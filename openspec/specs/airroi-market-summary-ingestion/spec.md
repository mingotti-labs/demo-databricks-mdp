# airroi-market-summary-ingestion Specification

## Purpose
Ingests AirROI's short-term rental market summary data for three
confirmed real markets (Vitória da Conquista/BA, Urubici/SC, Tauranga/NZ)
into `bronze_airroi`, modeled as SCD2 history in `bronze_airroi_publish` —
this project's first paid, authenticated API source, requiring deliberate
cost discipline throughout.

## Requirements

### Requirement: AirROI fetch helper
`src/common/airroi.py` SHALL provide a function that performs an
authenticated HTTP POST against AirROI's `/markets/summary` endpoint for
a given `country`/`region`/`locality`, sent as a nested `market` object
(not flat top-level fields — AirROI's own published example for this
endpoint is incorrect, confirmed via a real `422` response), using
`X-API-KEY` header auth with the key retrieved via
`dbutils.secrets.get("airroi", "api_key")`, and returning the parsed JSON
response.

#### Scenario: Helper works against the real API
- **WHEN** the helper is called with a real market's `country`, `region`,
  and `locality` (display names, not URL slugs)
- **THEN** the call succeeds and returns the real response shape
  (`market` as a `{locality, country, region, district}` map,
  `active_listings_count`, `average_daily_rate`, `occupancy`, `rev_par`,
  `revenue`, `booking_lead_time`, `length_of_stay`, `min_nights`) — not
  the field names shown in AirROI's own docs, confirmed wrong via the
  real successful response

### Requirement: Fixed market list, same across all environments
`market_summary_raw` SHALL pull exactly three markets — Vitória da
Conquista/BA, Urubici/SC, Tauranga/NZ — identically in `dev`, `tst`, and
`prd`. No per-environment row-limiting or subsetting SHALL be applied,
since there is no free-tier or smaller-sample concept for this source.

#### Scenario: Same three markets in every environment
- **WHEN** the pipeline is deployed and run against `dev`, `tst`, or `prd`
- **THEN** `market_summary_raw` has exactly 3 rows in every environment,
  representing the same three markets

### Requirement: Full-refresh batch ingestion into bronze_airroi
`market_summary_raw` SHALL be a Materialized View that re-fetches all
three markets' current summary on every run — the source has no
incremental cursor, so full-refresh batch pull is the correct approach.

#### Scenario: Pipeline run lands data
- **WHEN** the pipeline is run against a target
- **THEN** `<catalog>.bronze_airroi.market_summary_raw` exists and is
  populated with 3 rows

### Requirement: SCD2 modeling only, no SCD1
`market_summary_scd2` SHALL exist in `bronze_airroi_publish`, built via
`create_auto_cdc_from_snapshot_flow` against `market_summary_raw`
directly, keyed by the flat `_country`/`_region`/`_locality` columns
`market_summary_raw` carries alongside the API's own nested `market` map
— not the `market` map itself (Auto CDC's `keys=` needs flat columns, not
a nested struct/map type). No SCD1 table SHALL be built for this pattern
— a deliberate scope decision, since SCD1 would be pure duplication of
SCD2's `WHERE __END_AT IS NULL` filter.

#### Scenario: SCD2 table matches source row count on initial load
- **WHEN** the SCD pipeline is run after `market_summary_raw` is populated
- **THEN** `market_summary_scd2` has a row count matching
  `market_summary_raw` exactly (3 rows)

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`market_summary_raw` is populated with exactly 3 rows and that
`market_summary_scd2`'s row count matches it, chained into one job
(`verify_airroi_market_summary_pattern`) so the pattern can be re-checked
on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_airroi_market_summary_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
