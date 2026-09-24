## Why

Phase 3h adds a sixth source system: AirROI's short-term rental market
intelligence API, for four confirmed real markets — Vitória da Conquista/BA,
Urubici/SC, Tauranga/NZ, and Prado/BA (queried with `district="Cumuruxatiba"`,
a named neighborhood with no standalone market page of its own). Sydney was
explicitly dropped after confirming its plain `sydney` slug is a
generic/residual bucket on AirROI's own site, not a real Local Government
Area or the Greater Sydney metro; Tauranga has one accepted minor gap
(Papamoa, a real Tauranga suburb, is a separate sibling page and likely
excluded).

This is the project's **first source with a real, paid, authenticated
API** — every prior source is free/public. AirROI has no free sandbox;
every call costs real money — AirROI's general pricing page advertises
"$0.01/call" as a starting rate, but the user confirmed the actual charge
was $0.10/call, 10x that headline figure (not independently re-verified
from AirROI's own billing dashboard in this session — taken as the user's
real, observed cost). This shapes the design throughout: no
per-environment row-limiting (there's no "smaller sample" concept for a
fixed 4-market pull), a simple vendor-scoped fetch helper rather than a
full reusable connector (AirROI is one proprietary API, not a reusable
protocol like CKAN/ArcGIS), and deliberately minimal live testing before
wiring anything into a pipeline.

Two endpoints are pulled: `/markets/summary` (a single current snapshot per
market) and `/markets/metrics/all` (the time-series counterpart — a rolling
~12-month window of distribution metrics per market). Both endpoints'
documented request/response shapes turned out to be wrong, confirmed via
real calls, not assumed correct from docs.

This change also introduces the platform's two standard lineage timestamp
columns (`ingested_timestamp` on `_raw` tables, `transformed_timestamp` on
`_scd2` tables) — see NAMING.md's "Platform-added timestamp columns". AirROI
is the first source to carry them; earlier sources are not retrofitted as
part of this change.

## What Changes

- `src/common/airroi.py`: a small, source-scoped fetch helper —
  `fetch_market_summary(...)` and `fetch_market_metrics_all(...)`, each one
  HTTP POST per market to its respective endpoint with a nested `market`
  object body, `X-API-KEY` header auth (read via
  `dbutils.secrets.get("airroi", "api_key")`), matching UNGM's helper
  pattern. Safe to live in `src/common/` (not inlined) since these are plain
  functions called driver-side inside Materialized View bodies, not custom
  Spark DataSource classes.
- `bronze_airroi.market_summary_raw`: a Materialized View looping over the
  four fixed markets, stamped with `ingested_timestamp`
- `bronze_airroi.market_metrics_all_raw`: a Materialized View, one row per
  `(market, date)` (4 markets × ~12 months = 48 rows/run), metric fields
  kept as AirROI's own distribution structs (`{avg, p25, p50, p75, p90}`) —
  flattening is a silver concern, not bronze. Also stamped with
  `ingested_timestamp`
- `market_summary_scd2` / `market_metrics_all_scd2` in `bronze_airroi_publish`
  — **SCD2 only, no SCD1**, a deliberate scope decision: SCD1 would just be
  "current value per key," already recoverable from SCD2 via `WHERE
  __END_AT IS NULL`, so building both would be pure duplication. Both are
  fed via a `@dp.temporary_view()` that stamps `transformed_timestamp` on
  the raw source before the CDC flow, with both timestamp columns excluded
  via `track_history_except_column_list` (otherwise `current_timestamp()`'s
  per-run difference would make Auto CDC version every row every run).
- A standing verification suite (`verify_airroi_market_summary_pattern`)
  covering both endpoints' ingestion and SCD modeling
- `docs/source_systems/`: reference docs for this source (and, for platform
  completeness, every other source system) — endpoints, real vs. documented
  shapes, auth, known gotchas. AirROI's includes a metrics glossary
  (`rev_par`/`revpar`, `revenue`, `occupancy`, etc.)

## Capabilities

### New Capabilities
- `airroi-market-summary-ingestion`: fetch-helper-based ingestion of
  AirROI's market summary and market metrics data into `bronze_airroi`,
  with SCD2-only modeling into `bronze_airroi_publish`

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3h-airroi-schema` (merged) — this
change writes into `bronze_airroi`/`bronze_airroi_publish` and reads the
`airroi` secret scope's `api_key`, both of which that change created.

## Rollout

`dev` and `prd` both get a real pipeline run (real API cost in each).
`tst` gets the code deployed via CI/CD like every environment, but is not
separately run with real API calls — `tst`'s configuration is identical to
`dev`'s (same fixed market list, no per-environment row-limiting for this
source), so a `tst` run would duplicate cost without exercising anything
`dev`'s run doesn't already prove.

## Impact

- Adds `src/common/airroi.py`, new pipeline resource(s), and a verification
  job to the bundle across `dev`/`tst`/`prd`
- No changes to any existing source system's resources
- **Real, non-trivial dollar cost per pipeline run** — `market_summary_raw`
  (4 calls × $0.10 = $0.40) + `market_metrics_all_raw` (4 calls × $0.10 =
  $0.40) = $0.80/run, unlike every other source in this project. Every full
  environment rollout (`dev` + `prd`, `tst` skipped per Rollout above) costs
  ~$1.60 total.
