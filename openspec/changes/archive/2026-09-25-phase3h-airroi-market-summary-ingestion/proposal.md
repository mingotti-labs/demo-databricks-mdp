## Why

Phase 3h adds a sixth source system: AirROI's short-term rental market
intelligence API (`/markets/summary`), for three confirmed real markets —
Vitória da Conquista/BA, Urubici/SC, Tauranga/NZ. Sydney was explicitly
dropped after confirming its plain `sydney` slug is a generic/residual
bucket on AirROI's own site, not a real Local Government Area or the
Greater Sydney metro; Tauranga has one accepted minor gap (Papamoa, a real
Tauranga suburb, is a separate sibling page and likely excluded).

This is the project's **first source with a real, paid, authenticated
API** — every prior source is free/public. AirROI has no free sandbox;
every call costs real money — AirROI's general pricing page advertises
"$0.01/call" as a starting rate, but the user confirmed the actual charge
for `/markets/summary` calls was $0.10/call, 10x that headline figure (not
independently re-verified from AirROI's own billing dashboard in this
session — taken as the user's real, observed cost). This shapes the design
throughout: no per-environment row-limiting (there's no "smaller sample"
concept for a 3-market aggregate pull), a simple vendor-scoped fetch
helper rather than a full reusable connector (AirROI is one proprietary
API, not a reusable protocol like CKAN/ArcGIS), and deliberately minimal
live testing before wiring into a pipeline.

## What Changes

- `src/common/airroi.py`: a small, source-scoped fetch helper —
  `fetch_market_summary(base_url, api_key, country, region, locality)` —
  one HTTP POST per market to `/markets/summary` with a nested `market`
  object body, `X-API-KEY` header auth (read via
  `dbutils.secrets.get("airroi", "api_key")`), matching UNGM's helper
  pattern. Safe to live in `src/common/` (not inlined) since this is a
  plain function called driver-side inside a Materialized View body, not
  a custom Spark DataSource class — the `src/common/` import constraint
  found for ACNC/NSW property only affects DataSource classes, confirmed
  in this project's own history. **Both the request shape and every
  response field name differ from AirROI's own published docs** —
  confirmed via a real `422` error and the real successful response, not
  trusted from documentation; see design.md for the full correction
- `bronze_airroi.market_summary_raw`: a Materialized View that loops over
  the three fixed markets (one bundle-configured list, same across
  `dev`/`tst`/`prd` — no row-limiting, since 3 calls is already minimal)
- `market_summary_scd2` in `bronze_airroi_publish` — **SCD2 only, no
  SCD1**, a deliberate scope decision: SCD1 would just be "current value
  per key," already recoverable from SCD2 via `WHERE __END_AT IS NULL`, so
  building both would be pure duplication for this source
- A standing verification suite (`verify_airroi_market_summary_pattern`)

## Capabilities

### New Capabilities
- `airroi-market-summary-ingestion`: fetch-helper-based ingestion of
  AirROI's market summary data into `bronze_airroi`, with SCD2-only
  modeling into `bronze_airroi_publish`

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3h-airroi-schema` (merged) — this
change writes into `bronze_airroi`/`bronze_airroi_publish` and reads the
`airroi` secret scope's `api_key`, both of which that change created.

## Impact

- Adds `src/common/airroi.py`, new pipeline resource(s), and a
  verification job to the bundle across `dev`/`tst`/`prd`
- No changes to any existing source system's resources
- **Real, non-trivial dollar cost per pipeline run** (3 calls × whatever
  AirROI's actual per-call rate is for this endpoint) — unlike every
  other source in this project
