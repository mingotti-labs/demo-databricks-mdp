## Why

Bronze Publish now exposes cleaned, uniquely-keyed SCD1/SCD2 objects for all
six ingested sources (neon, clickstream, ungm, acnc, nsw_spatial, airroi),
but nothing downstream consumes them yet. This change builds Silver
Landing, the first Silver sub-layer defined in `docs/medallion/silver.md`,
giving every source a one-to-one, source-aligned foothold in Silver so
later sub-layers (Normalised, Domain, Marts) have a stable, standardized
starting point instead of reading Bronze Publish directly.

## What Changes

- New `silver_landing_{source}` schema and materialized-view tables for all
  10 entities currently in Bronze Publish, one schema per source system.
- SCD variant selection precedence (SCD2 > SCD1 > SCD0) codified in
  `silver.md` and applied here: customers/products (neon), unspsc_public
  (ungm), charity_register (acnc), property (nsw_spatial),
  market_metrics_all/market_summary (airroi) land from their SCD2 object;
  orders/order_items (neon) and web_events (clickstream) land from SCD1,
  since no SCD2 variant exists for them. Where a Python and SQL
  implementation both exist for the same SCD1 object (neon orders/
  order_items, clickstream web_events), the Python variant is canonical.
- `silver.md` materialization rule added: Materialized View is the default
  for any Bronze Publish SCD1/SCD2 source, because those sources are
  upsert-maintained (not append-only) — a Streaming Table read against them
  fails at runtime, a fact already proven by `phase3b-neon-scd-modeling`.
- `silver.md` and `NAMING.md` corrected: Silver Landing stamps
  `transformed_timestamp` (not `ingested_timestamp`, which `NAMING.md`
  already reserves as immutable past `_raw`) for its own refresh time,
  propagating `ingested_timestamp` unchanged where Bronze Publish already
  provides one (currently AirROI only).
- `silver.md` updated to defer surrogate-key generation to a later Silver
  sub-layer; Silver Landing only carries one through if Bronze Publish
  already provides it (none currently do), so natural key(s) lead as the
  first column(s) instead.
- `silver.md` records the future Silver Normalised orchestration
  convention (pipeline and job naming) so it slots in without renaming
  Landing resources later.
- New `docs/medallion/data-sources.md`: authoritative registry of every
  Bronze Publish source, its SCD variants, and what currently consumes it
  downstream.
- Six new Lakeflow Declarative Pipelines, one per source
  (`silver--landing--{source}--${bundle.target}`), each grouping that
  source's Silver Landing tables — mirrors Bronze Publish's existing
  per-source pipeline grouping.

## Capabilities

### New Capabilities
- `silver-landing`: source-aligned Silver Landing tables exposing Bronze
  Publish data into Silver, one schema per source, with standardized
  provenance metadata, SCD-variant selection, and row-count parity with
  Bronze.

### Modified Capabilities
(none — no existing tracked spec's requirements change; `silver.md` is
project documentation, not a tracked openspec capability)

## Impact

- Affected code: new `src/layers/silver/landing/{source}/*.py` modeling
  files; new `resources/pipelines/silver_landing_{source}.pipeline.yml`
  bundle resources for six pipelines.
- Affected docs: `docs/medallion/silver.md` (materialization rule,
  surrogate-key deferral, SCD precedence, orchestration convention,
  provenance timestamp column — all already applied), `NAMING.md`
  (resolves the Silver Landing/Normalised schema naming, generalizes
  `transformed_timestamp` beyond bronze), `docs/registers/data-sources.md`
  (new), `docs/decision-register.md` (new).
- No changes to any existing Bronze Publish object or pipeline — this
  change only reads from them.
- No breaking changes.
