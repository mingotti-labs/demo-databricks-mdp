## Context

See proposal.md - Why. `docs/medallion/silver.md` defines Silver Landing's
conventions (naming, provenance, materialization rule, surrogate-key
deferral, SCD precedence) — this change is the first to apply them, and the
conventions were sharpened as part of this same change (materialization
rule and surrogate-key deferral were added to `silver.md` here, not
pre-existing).

Bronze Publish currently has 10 entities across 6 source schemas (full
inventory in `docs/medallion/data-sources.md`):

| Source | Entity | Selected Bronze Publish object | Natural key(s) |
|---|---|---|---|
| neon | customers | `customers_scd2` (Python) | id |
| neon | products | `products_scd2` (Python) | id |
| neon | orders | `orders_scd1` (Python) | id |
| neon | order_items | `order_items_scd1` (Python) | id |
| clickstream | web_events | `web_events_scd1` (Python) | event_id |
| ungm | unspsc_public | `unspsc_public_scd2` | Id |
| acnc | charity_register | `charity_register_scd2` | ABN |
| nsw_spatial | property | `property_scd2` | addressstringoid |
| airroi | market_metrics_all | `market_metrics_all_scd2` | _country, _region, _locality, _district, date |
| airroi | market_summary | `market_summary_scd2` | _country, _region, _locality, _district |

All 10 selected objects are Databricks Auto CDC outputs (`create_streaming_table`
+ `create_auto_cdc_flow`/`create_auto_cdc_from_snapshot_flow`), which are
upsert-maintained, not append-only.

## Goals / Non-Goals

**Goals:**
- Land all 10 entities above into Silver Landing, one schema per source
  (`silver_landing_{source}`), one table per entity
- Apply the SCD2 > SCD1 > SCD0 precedence and Python-canonical rules
  uniformly, with no per-entity exceptions
- Materialize every table per `silver.md`'s new materialization rule
- Group pipelines per source system (6 pipelines total), matching Bronze
  Publish's existing convention

**Non-Goals:**
- Silver Normalised, Domain, or Marts sub-layers — future changes
- Generating a surrogate key — deferred to a later Silver sub-layer per
  `silver.md`
- Cross-source joins or business-specific mappings — explicitly out of
  scope for Silver Landing
- A Landing→Normalised orchestration job — `silver.md` records the future
  naming convention, but the job itself has no Normalised pipeline to
  depend on yet

## Decisions

**Materialized View, not Streaming Table, for all 10 tables.**
Every selected Bronze Publish object is an Auto CDC SCD1/SCD2 output —
upsert-maintained, not append-only. `phase3b-neon-scd-modeling` already
proved a streaming read against this shape of table fails at runtime
(`DELTA_SOURCE_TABLE_IGNORE_CHANGES`). A plain View was also considered and
rejected: every table here adds provenance columns and (for SCD2 sources)
an `is_current` derivation, and a data-quality expectation that must
actually drop/fail bad rows needs a materialized output — expectations on a
plain View are metrics-only.

**Table name drops the Bronze Publish SCD suffix.**
`silver_landing_neon.customers`, not `silver_landing_neon.customers_scd2`.
The chosen SCD variant is a Bronze-internal precedence decision (SCD2 today
for this entity), not part of the entity's identity in Silver — if a future
Bronze Publish change adds a richer variant for an entity that currently
only has SCD1, the precedence rule picks the new object automatically
without renaming the Silver Landing table underneath existing consumers.

**`is_current` computed from the Bronze Publish SCD2 end-of-validity
column.**
For the 7 SCD2-sourced tables, `is_current` is
`CASE WHEN <end column> IS NULL THEN true ELSE false END`, reusing
`silver.md`'s existing standard of renaming Auto CDC's end-of-validity
column to `scd_valid_to_timestamp`. No new source data is needed.

**`transformed_timestamp`, not `ingested_timestamp`, is Silver Landing's own
refresh-time column.**
`NAMING.md` already defines `ingested_timestamp` as stamped exactly once,
at Bronze `_raw`, and never changed downstream — restamping it here would
corrupt that meaning (caught by reading `NAMING.md` before committing this
change; see `docs/decision-register.md`'s 2026-09-25 "provenance timestamp
column name" entry). Silver Landing is a transformation step, so it stamps
`transformed_timestamp` with `current_timestamp()` at its own refresh
instead — `NAMING.md`'s existing column for exactly this, generalized from
"the bronze `_scd1`/`_scd2` layer" to any transformation layer.
`ingested_timestamp` is propagated unchanged when the selected Bronze
Publish object already has one (currently only AirROI's two entities, per
`NAMING.md`'s note that the column isn't yet retrofitted to the other five
sources); absent otherwise. Silver Landing does not backfill it — that is
bronze-layer work, out of scope here per this change's non-goals.

**`source_file_name` is null except for clickstream.**
Only clickstream's Bronze ingestion (Auto Loader) is file-based; the other
five sources are DB/API pulls with no source file to record.

**Six pipelines (one per source), not one shared pipeline or ten per-entity
pipelines.**
Matches Bronze Publish's existing per-source pipeline grouping exactly
(e.g. `neon_scd_modeling_python.pipeline.yml` covers all of Neon's Bronze
Publish tables). Keeps failure blast radius scoped to one source without
the operational overhead of a pipeline per entity. Pipeline naming:
`silver--landing--{source}--${bundle.target}`, reserving
`silver--normalised--{source}--${bundle.target}` and a
`silver--{source}--${bundle.target}` orchestrating job for when Silver
Normalised exists (recorded in `silver.md`'s Orchestration section).

## Risks / Trade-offs

- [Materialized Views recompute rather than stream incrementally, so
  refresh cost grows with Bronze Publish table size] → Mitigation:
  acceptable at current demo scale; the same batch-recompute trade-off is
  already accepted for Bronze Publish's own SCD2 snapshot flows.
- [Nothing in this change enforces that a Silver Landing refresh runs after
  its Bronze Publish source has finished refreshing, so the row-count
  parity gate could compare against a stale or partially-refreshed Bronze
  state] → Mitigation: out of scope here — no Landing→Bronze orchestration
  job exists yet in this project; acceptable since pipelines are currently
  run manually/on independent schedules. Will be tightened once the
  Landing→Normalised job (and, by extension, any Bronze→Landing ordering)
  is designed.
- [Six independent pipelines is six places conventions could drift] →
  Mitigation: conventions live in `silver.md`, not duplicated per pipeline;
  a future convention change is a shared read for all six, not six
  rewrites.

## Migration Plan

Additive only — no existing Bronze Publish object or pipeline changes.
Deploy the six new pipelines to `dev`, run each once, and verify per
entity: (a) row count matches the selected Bronze Publish source object,
(b) provenance columns are populated — non-null `source_name`/
`transformed_timestamp` on all 10 tables, `source_file_name` non-null only
for clickstream, and `ingested_timestamp` present and non-null only for
AirROI's two entities (absent elsewhere, not a bug), (c) for the 7
SCD2-sourced tables, `is_current` correctly reflects the active version,
(d) natural key(s) are the leading column(s) with no surrogate key column
present, (e) schema/table names match `silver_landing_{source}.{entity}`.
Rollback: drop the six new schemas and pipelines; nothing else depends on
them.
