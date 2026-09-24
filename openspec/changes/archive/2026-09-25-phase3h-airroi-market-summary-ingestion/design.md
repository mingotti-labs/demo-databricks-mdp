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
6. A fourth market, Cumuruxatiba/BA, was added later. It has no standalone
   market page — it only appears as a named neighborhood within Prado's
   report. Queried as `locality="Prado"` + `district="Cumuruxatiba"` (the
   `market` object's fourth, optional field, unused by the other three
   markets). Before committing to this, `district` was confirmed genuinely
   functional (not silently ignored) via a real before/after comparison:
   `locality="Prado"` alone returns 1,102.7 active listings; adding
   `district="Cumuruxatiba"` returns 360.6 — a real, different subset.

A second endpoint, `/markets/metrics/all`, was added after the first
(`/markets/summary`) was already working — the time-series/pacing
counterpart the user asked for by name once they understood
`/markets/summary` only gives one current point per market.

## Goals / Non-Goals

**Goals:**
- Land AirROI's market summary and market metrics data for the four
  confirmed markets, modeled as SCD2 history
- Keep real-dollar-cost API usage minimal and deliberate — no
  free-and-easy retries the way every prior source allowed
- Introduce the platform's `ingested_timestamp`/`transformed_timestamp`
  lineage columns, starting with this source

**Non-Goals:**
- SCD1 — a deliberate scope decision (see proposal.md), not a technical
  limitation
- The individual-listings endpoints (`/listings/*`) — the user's own plan
  is to size any such pull using `active_listings_count` this change's
  data surfaces, so that's explicitly a later, separate increment
- Per-environment row-limiting — there's no "smaller sample" concept for
  a fixed 4-market aggregate pull; `dev`/`tst`/`prd` all use the same
  market list
- A generic/reusable AirROI connector class — this is one proprietary
  vendor's API, not a reusable protocol like CKAN/ArcGIS REST; a plain
  fetch helper (UNGM's pattern) is the right level of abstraction
- Retrofitting `ingested_timestamp`/`transformed_timestamp` onto earlier
  sources (ACNC, NSW Spatial, UNGM, Neon, clickstream) — deferred to a
  later, separate change, since it touches resources unrelated to AirROI

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
without issue). Both AirROI helpers are the latter shape, so `src/common/`
is the right, already-proven-working location.

**`/markets/summary` request shape corrected via a real `422` response —
AirROI's own published example for this endpoint was wrong.**
The docs' shown example (`{"country_code": "us", "state": "florida",
"city": "miami-beach"}`) does not match the endpoint's real requirements.
The actual first live call returned `422` with an explicit error body:
`"'country', 'region', and 'locality' fields are all required... market
must not be null"` — the real shape is a nested `market` object
(`{"market": {"country": ..., "region": ..., "locality": ...}}`), matching
the general API overview's hierarchical model, not the flat shape shown
for this specific endpoint. Values are **display names**, not URL slugs
(`"Vitória da Conquista"`, not `"vitória-da-conquista"`) — confirmed by
the second, successful call using that shape. `/markets/metrics/all` uses
the identical request shape, confirmed via its own successful test call.

**Response fields also don't match AirROI's docs — confirmed via the real
successful responses, used as-is rather than the documented names.**
`/markets/summary` real fields: `active_listings_count`,
`average_daily_rate`, `occupancy`, `rev_par`, `revenue`,
`booking_lead_time`, `length_of_stay`, `min_nights`, and a structured
`market` map (`{locality, country, region, district}`, echoing the
request). None of these match the docs' example response
(`active_listings`, `average_adr`, `average_occupancy`, `average_revpar`,
`median_annual_revenue`, `avg_booking_lead_time_days`,
`avg_length_of_stay_nights`, `currency`). No `currency` field is returned
at all (presumed USD, not explicitly confirmed).

`/markets/metrics/all` real response is a different shape again: `{market,
results}`, where `results` is a rolling ~12-month array of `{date,
occupancy, average_daily_rate, revpar, revenue, booking_lead_time,
length_of_stay, min_nights, active_listings_count}` — every metric except
`active_listings_count` is a **distribution object**
(`{avg, p25, p50, p75, p90}`), not the single value `/markets/summary`
returns. Note the field is `revpar` here vs. `rev_par` in `/markets/summary`
— a confirmed, real inconsistency between the two endpoints.

**SCD key is the flat `_country`/`_region`/`_locality`/`_district` columns
each `_raw` table carries, not the API's `market` map, and not a synthetic
concatenated string.**
`create_auto_cdc_from_snapshot_flow`'s `keys=` needs flat columns, not a
struct/map type, so each raw pipeline tags every row with flat
`_country`/`_region`/`_locality`/`_district` columns (`_district` is `NULL`
for the three markets that don't use it) alongside the API's own nested
`market` field, and the SCD flows key on those flat columns directly. (An
earlier draft of this design considered a synthetic `country|state|city`
string key instead — superseded once the flat-column approach was actually
implemented and proven to work; the synthetic-string idea was never built.)
`market_metrics_all_scd2` additionally keys on `date`, since each `(market,
date)` pair — not each market alone — is the addressable entity for that
table.

**No incremental cursor — full-refresh batch pull, same as every other
custom-API source.**
Both raw tables re-fetch all four markets' current data on every run.
`create_auto_cdc_from_snapshot_flow` (SCD2 only) tracks how each market's
stats change between runs — for `market_summary`, that's a genuinely
meaningful history for a "seasonality curves" investment story; for
`market_metrics_all`, it additionally captures how AirROI *revises* a given
future month's forecast as it approaches, which a plain append-only landing
would lose.

**`ingested_timestamp`/`transformed_timestamp` must be excluded from
`track_history_except_column_list`, or SCD2 breaks silently.**
`current_timestamp()` differs on every single run. Without excluding both
columns, Auto CDC treats every row as changed on every run (since the
timestamp column itself always differs), creating a spurious new SCD2
history version each time regardless of whether the real source data
changed — silently turning "history of real changes" into "history of
every run." Confirmed via a real multi-run test: row counts stayed correct
(4 current rows in `market_summary_scd2`, 48 in `market_metrics_all_scd2`,
matching total row counts with zero accumulated history) only once the
exclusion was added; this was caught before it could accumulate junk
history, not after.

## Risks / Trade-offs

- [No free sandbox means every test run costs real money] → Realized, not
  just theoretical, multiple times across this change's lifetime:
  - `/markets/summary`'s first real run failed with a `422` (wrong request
    shape), costing 1 call before failing fast; the retry after fixing the
    code cost 3 more calls (successful 3-market run at the time).
  - Diagnosing whether `district` was genuinely honored for Cumuruxatiba
    took a real before/after comparison call plus several failed attempts
    at a Spark `CANNOT_DETERMINE_TYPE` error while trying to build a
    diagnostic DataFrame from heterogeneous API responses — resolved by
    deliberately raising the raw dict in a `ValueError` to force it into
    visible output, bypassing DataFrame construction entirely.
  - Learning `/markets/metrics/all`'s real response shape cost exactly one
    $0.10 call (a single-market test, confirmed via the pipeline event log
    showing one `flow_progress ERROR`, not a retry storm) before building
    the full 4-market pipeline.
  - **Real per-call cost is $0.10, not the $0.01 AirROI's general pricing
    page advertises** — confirmed by the user's own observed charge, a 10x
    gap from the headline rate, not independently re-verified from AirROI's
    billing dashboard. Worth re-confirming before scaling call volume for
    anything beyond the current 4-market, 2-endpoint pattern.
- [AirROI's own published request/response examples don't match the real
  API, for either endpoint] → Confirmed, not assumed: both the request
  shape and every response field name differ from docs, for both
  `/markets/summary` and `/markets/metrics/all`. Fixed by trusting the real
  error bodies and real successful responses over documented examples —
  this project's evidence-over-documentation principle held even against
  the vendor's own docs, twice.
- [This source may be deactivated] → The user has explicitly flagged they
  may stop using AirROI if the data doesn't prove useful enough to justify
  the ongoing per-call cost. `docs/source_systems/airroi.md` exists
  specifically so the integration remains understandable independent of
  that decision.

## Migration Plan

Deploy to `dev` first, verify via `verify_airroi_market_summary_pattern`.
Deploy to `tst`/`prd` via CI/CD on merge to `main` (this repo's standard
promotion path). Trigger a real pipeline run in `prd` for consistency with
`dev`; skip a separate `tst` run — `tst`'s configuration is identical to
`dev`'s for this source (same fixed market list, no row-limiting), so it
would duplicate real-dollar cost without proving anything `dev`'s run
doesn't already prove. `tst` still gets the deployed code and could be run
later if that changes. Rollback: remove the resources from the bundle; both
raw tables only ever full-refresh, though SCD2 history would be lost.
