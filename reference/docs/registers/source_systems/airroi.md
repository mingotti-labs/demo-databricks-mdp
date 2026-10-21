# AirROI

Short-term rental (Airbnb/Vrbo-style) market intelligence API. This project's
**first source with a real, paid, authenticated API** — every other source is
free/public. No free sandbox exists; every call costs real money.

- Base URL: `https://api.airroi.com` (bundle variable `airroi_base_url`, fixed
  across `dev`/`tst`/`prd` — no test vs. production split like UNGM/ACNC)
- Auth: API key in an `X-API-KEY` header. Stored as the `airroi` UC secret
  scope's `api_key` key (`demo-databricks-iac`, `phase3h-airroi-schema`),
  sourced from the root-level `airroi_api_key` Terraform variable (set directly
  in HCP Terraform as a `sensitive` workspace variable — never committed).
- **Real per-call cost is $0.10, not the $0.01 AirROI's general pricing page
  advertises** — confirmed via the user's own observed charge, a 10x gap from
  the headline rate. Re-confirm before scaling call volume for any future work
  on this source.
- Code: `src/common/airroi.py` (plain source-scoped fetch helper, not a
  reusable connector — AirROI is one proprietary vendor's API, not a reusable
  protocol like CKAN/ArcGIS), `src/layers/bronze/airroi/*_raw.py`,
  `src/layers/bronze/airroi_publish/*_scd2.py`.
- **This source may be deactivated** if the data doesn't prove useful enough
  to justify the ongoing per-call cost — this doc exists so the integration
  can be understood (or resumed) independent of that decision.

## Markets used in this project

Four real markets, individually verified as clean, non-fragmented entries on
AirROI's own public site before use (free to check):

| Country | Region | Locality | District |
|---|---|---|---|
| Brazil | Bahia | Vitória da Conquista | — |
| Brazil | Santa Catarina | Urubici | — |
| New Zealand | Bay of Plenty | Tauranga | — |
| Brazil | Bahia | Prado | Cumuruxatiba |

- **Sydney was dropped**: its plain `sydney` slug sits alongside 50+ separate
  Sydney-suburb pages (Bondi, Surry Hills, Parramatta, etc.), strongly
  indicating a generic/residual bucket, not a real Local Government Area or
  the Greater Sydney metro.
- **Tauranga has one accepted minor gap**: Papamoa, a real Tauranga suburb, is
  a separate sibling page, likely excluded from `tauranga`'s figures.
- **Cumuruxatiba has no standalone market** — it's a named neighborhood within
  Prado's report, queried as `locality="Prado"` + `district="Cumuruxatiba"`.
  `district` is confirmed genuinely functional (not silently ignored) via a
  real before/after call: `locality="Prado"` alone returns 1,102.7 active
  listings; adding `district="Cumuruxatiba"` returns 360.6 — a real, different
  subset.

The request body's `market` object uses **display names** (e.g. `"Vitória da
Conquista"`), not URL slugs and not the flat `country_code`/`state`/`city`
shape AirROI's own docs show (that shape returns a real `422` — confirmed, not
assumed).

## Endpoints used in this project

### `POST /markets/summary`

Single current snapshot per market. Both AirROI's own published request and
response examples for this endpoint are wrong — confirmed via real calls, not
assumed correct from docs.

Request:
```json
{"market": {"country": "Brazil", "region": "Bahia", "locality": "Vitória da Conquista", "district": null}}
```

Real response shape (docs claim `active_listings`, `average_adr`,
`average_occupancy`, `average_revpar`, `median_annual_revenue`,
`avg_booking_lead_time_days`, `avg_length_of_stay_nights`, `currency` — none
of that matches):
```json
{
  "market": {"country": "...", "region": "...", "locality": "...", "district": null},
  "active_listings_count": 1102.7,
  "average_daily_rate": 603.1,
  "occupancy": 0.25,
  "rev_par": 156.3,
  "revenue": 4690.6,
  "booking_lead_time": 29.8,
  "length_of_stay": 2.3,
  "min_nights": 1.5
}
```

Lands in `bronze_airroi.market_summary_raw` (one row per market), modeled as
`market_summary_scd2` in `bronze_airroi_publish` — SCD2 only, no SCD1 (SCD1
would just duplicate SCD2's `WHERE __END_AT IS NULL` filter). Keyed on the
flat `_country`/`_region`/`_locality`/`_district` columns the raw table
carries (not the API's nested `market` map — Auto CDC's `keys=` needs flat
columns).

### `POST /markets/metrics/all`

Time-series counterpart to `/markets/summary` — a rolling ~12-month window
(one trailing month + ~11 forward-looking/pacing months), each metric a
**distribution**, not a single value:

```json
{
  "market": {"country": "...", "region": "...", "locality": "...", "district": null},
  "results": [
    {
      "date": "2025-09-01",
      "occupancy": {"avg": 0.25, "p25": 0.11, "p50": 0.21, "p75": 0.36, "p90": 0.51},
      "average_daily_rate": {"avg": 603.1, "p25": 373.4, "p50": 549.5, "p75": 765.2, "p90": 1004.5},
      "revpar": {"avg": 156.3, "p25": 49.5, "p50": 114.3, "p75": 202.9, "p90": 357.3},
      "revenue": {"avg": 4690.6, "p25": 1482.6, "p50": 3427.2, "p75": 6088.5, "p90": 10720.1},
      "booking_lead_time": {"avg": 29.8, "p25": 6.0, "p50": 18.0, "p75": 40.0, "p90": 75.0},
      "length_of_stay": {"avg": 2.3, "p25": 1.0, "p50": 2.0, "p75": 3.0, "p90": 4.0},
      "min_nights": {"avg": 1.5, "p25": 1.0, "p50": 1.0, "p75": 2.0, "p90": 2.0},
      "active_listings_count": 1007
    }
  ]
}
```

Note the field name is `revpar` here vs. `rev_par` in `/markets/summary` — a
real, confirmed inconsistency between the two endpoints, not a typo in this
doc.

Lands in `bronze_airroi.market_metrics_all_raw` as one row per `(market,
date)`, metric structs kept as-is (flattening percentiles into columns is a
silver concern, not bronze). Modeled as `market_metrics_all_scd2`, keyed on
`_country`/`_region`/`_locality`/`_district`/`date` — SCD2 here tracks how
AirROI *revises* a given future month's forecast between pulls, a different
reason than `market_summary`'s "track the evolving current value." 4 markets ×
12 months = 48 rows/run; every run re-calls the API for all 4 markets
(Materialized View, always fully recomputed) — 4 × $0.10 = $0.40/run, same
cost profile as `market_summary_raw`.

## Metrics glossary

Definitions as understood from real response data and a sanity check against
known relationships — not copied from AirROI's docs, which don't define these
either.

- **`occupancy`** — fraction of available nights booked (0-1 scale, e.g. 0.25
  = 25% occupied).
- **`average_daily_rate` (ADR)** — average nightly rate for booked nights.
- **`rev_par` / `revpar`** (RevPAR, Revenue Per Available Room/listing) —
  industry-standard metric = `ADR × Occupancy`. Sanity-checked against real
  data and matches closely (e.g. Urubici: `603.1 × 0.25 ≈ 150.8`, vs. reported
  `156.3` — close enough to confirm the standard formula holds here).
- **`revenue`** — total revenue for the period. **Exact time period is not
  confirmed** — a rough sanity check against `ADR × 365 × occupancy` didn't
  match closely enough to confidently call it "annual," unlike `rev_par`. Do
  not assume an annualized figure without further verification (e.g. checking
  whether `revenue` scales consistently across `/markets/metrics/all`'s
  monthly rows).
- **`active_listings_count`** — count of active listings in the market at
  query time. Useful normalized against real city population (a
  listings-per-capita view) to flag oversupply/undersupply, cross-referenced
  with `occupancy` as a more direct signal — discussed, not yet implemented as
  silver/gold-layer logic.
- **`booking_lead_time`** — days between booking and check-in.
- **`length_of_stay`** — nights per booking.
- **`min_nights`** — the minimum-nights restriction hosts set, aggregated
  across listings.
- Percentile fields (`p25`/`p50`/`p75`/`p90`, `/markets/metrics/all` only) —
  standard percentile distribution across listings in the market for that
  metric/month; `p50` is the median, `avg` is the mean (not necessarily equal
  to `p50` if the distribution is skewed, which short-term rental pricing
  typically is).

## Full endpoint catalog (researched, not all implemented)

33 endpoints total, researched during Phase 3h scoping. Only `/markets/summary`
and `/markets/metrics/all` are implemented; the rest are documented here for
future reference if this source stays active.

**Listing Endpoints (12)**: `/listings`, `/listings/batch`,
`/listings/comparables`, `/listings/metrics/all`, `/listings/live/*` (several),
`/listings/search/*` (several).

**Market Endpoints (13)**: `/markets/summary`, `/markets/metrics/all`,
`/markets/metrics/{occupancy,average-daily-rate,revpar,revenue,booking-lead-time,length-of-stay,active-listings,min-nights}`
(single-metric variants of `/markets/metrics/all`), `/markets/metrics/future/pacing`,
`/markets/search`, `/markets/lookup`.

**Calculator (1)**: `/calculator/estimate`.

**Price Recommendation (2)**: two endpoints, not individually catalogued here
— revisit AirROI's docs directly if this becomes relevant.

`/listings/metrics/all` is the individual-listing-level counterpart to
`/markets/metrics/all` — deferred; would need `active_listings_count` from
already-landed data to size a reasonable per-market listing sample before
calling it, given the real per-call cost.
