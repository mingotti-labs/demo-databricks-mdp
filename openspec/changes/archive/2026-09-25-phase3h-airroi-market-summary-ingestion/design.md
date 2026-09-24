## Context

See proposal.md - Why. Originated from a pasted AI-generated prompt about
an "AirDNA" ingestion pipeline for two Brazilian cities; the actual
implementation deliberately diverges from that prompt's literal
prescriptions (a single monolithic `bronze_to_silver_pipeline.py` script,
OAuth2 client-credentials auth, a from-scratch deployment walkthrough) in
favor of this project's own established conventions — the user's own
explicit instruction was "the story in the prompt is more important" than
its literal code. AirDNA itself was investigated and rejected: Enterprise-only
API, ~$50K+/year, requires sales negotiation — not accessible for a
personal project. AirROI was found as a genuinely self-serve alternative
(instant API key, pay-per-call, no contracts) after also checking Key Data
Dashboard (demo-request-gated, rejected for the same reason as AirDNA).

Markets evolved during scoping, each change grounded in real evidence, not
assumption:
1. Original prompt: Salvador/BA + Sumaré/SP (illustrative, not committed)
2. Corrected to: Vitória da Conquista/BA + Urubici/SC
3. Expanded to include Tauranga/NZ + Sydney/AU
4. Sydney dropped after confirming (via AirROI's own public market pages,
   free to check) that its plain `sydney` slug sits alongside 50+ separate
   Sydney-suburb pages (Bondi, Surry Hills, Parramatta, North Sydney,
   etc.) — a strong signal it's a generic/residual bucket, not a real LGA
   or the Greater Sydney metro aggregate. Using it would have
   misrepresented what was actually being measured.
5. The remaining three markets were individually verified clean
   (non-fragmented) the same way: Vitória da Conquista and Urubici both
   confirmed as whole-city entries with no suburb siblings (via Bahia's
   and Santa Catarina's state pages); Tauranga confirmed mostly clean but
   with one real caveat — Papamoa (a genuine Tauranga suburb) is a
   separate sibling page, so `tauranga` likely excludes it. Accepted as a
   minor, documented gap (one suburb, not the wholesale fragmentation
   Sydney had), not a blocker.

## Goals / Non-Goals

**Goals:**
- Land AirROI's market summary data for the three confirmed markets,
  modeled as SCD2 history
- Keep real-dollar-cost API usage minimal and deliberate — no
  free-and-easy retries the way every prior source allowed

**Non-Goals:**
- SCD1 — a deliberate scope decision (see proposal.md), not a technical
  limitation
- The individual-listings endpoint (`/listings/search/market`) — the
  user's own plan is to size that pull using `active_listings` counts
  this change's data will surface, so it's explicitly a later, separate
  increment, not bundled in here
- Per-environment row-limiting — there's no "smaller sample" concept for
  a fixed 3-market aggregate pull; `dev`/`tst`/`prd` all use the same
  market list
- A generic/reusable AirROI connector class — this is one proprietary
  vendor's API, not a reusable protocol like CKAN/ArcGIS REST; a plain
  fetch helper (UNGM's pattern) is the right level of abstraction, not
  overengineered into a connector framework

## Decisions

**Fetch helper in `src/common/airroi.py`, not inlined — this is safe here,
unlike the CKAN/ArcGIS connectors.**
ACNC's `phase3d-acnc-charity-register-ingestion` confirmed that custom
Spark **DataSource classes** are cloudpickled for execution in a separate
worker process that doesn't inherit the driver's `sys.path`. That finding
is specific to `DataSource`/`DataSourceReader` classes registered via
`spark.dataSource.register()` — it does not apply to a plain function
called driver-side inside a `@dp.materialized_view()` body (exactly how
UNGM's `fetch_ungm_endpoint` already works, imported from `src/common/`
without issue). AirROI's helper is the latter shape, so `src/common/`
is the right, already-proven-working location.

**Request shape corrected via a real `422` response — AirROI's own
published example for this endpoint was wrong.**
The docs' shown example (`{"country_code": "us", "state": "florida",
"city": "miami-beach"}`) does not match the endpoint's real requirements.
The actual first live call returned `422` with an explicit error body:
`"'country', 'region', and 'locality' fields are all required... market
must not be null"` — the real shape is a nested `market` object
(`{"market": {"country": ..., "region": ..., "locality": ...}}`), matching
the general API overview's hierarchical model, not the flat shape shown
for this specific endpoint. Values are **display names**, not URL slugs
(`"Vitória da Conquista"`, not `"vitória-da-conquista"`) — confirmed by
the second, successful call using that shape.

**Response fields also don't match AirROI's docs — confirmed via the
real successful response, used as-is rather than the documented names.**
Real fields: `active_listings_count`, `average_daily_rate`, `occupancy`,
`rev_par`, `revenue`, `booking_lead_time`, `length_of_stay`, `min_nights`,
and a structured `market` map (`{locality, country, region, district}`,
echoing the request). None of these match the docs' example response
(`active_listings`, `average_adr`, `average_occupancy`, `average_revpar`,
`median_annual_revenue`, `avg_booking_lead_time_days`,
`avg_length_of_stay_nights`, `currency`) — that example was not trusted
for schema design once real data proved it wrong; `market_summary_raw`'s
actual columns are the real ones, not the documented ones. No `currency`
field is returned at all — presumed USD, not explicitly confirmed.

**SCD key is a synthetic `country_code|state|city` string, not the API's
returned `market` display field.**
The response only includes `market` as a human-readable label (e.g.
`"Miami Beach, Florida"`), not a stable identifier. Since the project
controls exactly what `country_code`/`state`/`city` values it sends for
each of the three fixed markets, concatenating those is a more
deterministic key than trusting the API's display-string formatting to
stay consistent across calls.

**No incremental cursor — full-refresh batch pull, same as every other
custom-API source.**
`market_summary_raw` re-fetches all three markets' current summary on
every run. `create_auto_cdc_from_snapshot_flow` (SCD2 only) tracks how
each market's stats change between runs — this is genuinely meaningful
history for a "seasonality curves" investment story, not a mechanical
passthrough.

## Risks / Trade-offs

- [No free sandbox means every test run costs real money] → Realized, not
  just theoretical: the first real run failed with a `422` (wrong request
  shape, AirROI's own docs were wrong), costing 1 call before failing
  fast (the market loop stops at the first error, so a retry after fixing
  the code cost 1 more call, not 3). Total cost across both failed
  attempts and the successful 3-market run: ~5 calls. **Real per-call
  cost turned out to be $0.10, not the $0.01 AirROI's general pricing
  page advertises** — confirmed by the user's own observed charge, a 10x
  gap from the headline rate, not independently re-verified from AirROI's
  billing dashboard in this session. ~5 calls ≈ $0.50, not "a few cents"
  — the fail-fast loop structure still kept this bounded rather than
  compounding, but the per-call economics are meaningfully worse than
  assumed when this change was scoped. Worth re-confirming the real rate
  before scaling call volume for anything beyond this fixed 3-market
  pattern (e.g. the deferred listings-endpoint follow-on, or any
  broader-market-scan idea like the Italy question raised and declined
  during this session).
- [AirROI's own published request/response examples don't match the real
  API] → Confirmed, not assumed: both the request shape and every
  response field name differ from docs. Fixed by trusting the real `422`
  error body and the real successful response over the documented
  examples — this project's evidence-over-documentation principle held
  even against the vendor's own docs, not just community/derived sources.

## Migration Plan

Deploy to `dev` first. Before wiring the helper into a pipeline, verify it
directly (outside Spark) against the real AirROI API with a minimal number
of calls — enough to confirm the request shape, auth, and diacritic
handling, not one call per market redundantly. Then deploy the pipeline,
run once against `dev`, verify via `verify_airroi_market_summary_pattern`,
promote to `tst`/`prd` the same way prior patterns were. Rollback: remove
the resources from the bundle; the pattern only ever full-refreshes on the
raw side, though SCD2 history would be lost.
