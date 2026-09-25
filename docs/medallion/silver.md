# Medallion Silver Design

Silver has the following sub-layers:
-- Landing
-- Normalised
-- Domain
-- Marts

## Silver Landing
### Purpose
Expose source specific data from Bronze Publish to Silver.
It can be considered a foundational data product.

### Characteristics
- Source-aligned
- Clean layer
- Allows standardatisation of columns, e.g., date
- Row count must mirror source systems
- no cross-source joins
- no business logic
- First data quality gate
- Uniqueness must be applied if bronze publish does not provide that through SCD1, SCD2 tables

### What fits here
- Source must be Bronze Publish
- If the same data source has more than one SCD object available in Bronze Publish, select by precedence: SCD2 > SCD1 > SCD0 (raw). Use the richer variant if it exists; fall back only when it doesn't. Usually only one variant should land in Silver
Provenance metadata (source_name, transformed_timestamp, source_file_name)
_rescued_data columns for schema-mismatch tolerance
Row-count parity checks vs Bronze

> **Discussion point (resolved 2026-09-25)** — this line originally read
> `ingested_timestamp`, which collides with `NAMING.md`'s "Platform-added
> timestamp columns": `ingested_timestamp` is stamped once at `_raw` and
> never changes downstream. Silver Landing is a transformation step, not
> an ingestion step, so it stamps `transformed_timestamp` instead — see
> [`docs/decision-register.md`](../decision-register.md#2026-09-25-silver-landing-provenance-timestamp-column-name).

### What does NOT fit here
- Normalisation
- Joins across sources
- Business rules (mappings)

### Materialisation when Databricks Native
Choice depends on whether the Bronze Publish source is append-only:

- **Materialized View (default)** — use when the Bronze Publish source is an
  Auto CDC SCD1/SCD2 object. These are upsert-maintained (rows updated in
  place when a tracked value changes or an SCD2 version closes out), not
  append-only. A Streaming Table read against them fails at runtime
  (`DELTA_SOURCE_TABLE_IGNORE_CHANGES`) — confirmed by a real failure
  recorded in `phase3b-neon-scd-modeling`'s design doc. Also required
  whenever this layer adds provenance columns, SCD column renames, an
  `is_current` derivation, or any data-quality expectation that must
  drop/quarantine rows — expectations on a plain View are metrics-only and
  cannot enforce the first data quality gate.
- **Streaming Table** — only when the Bronze Publish source is genuinely
  append-only (e.g. a raw event log that is never updated in place).
- **Plain View** — only when Bronze Publish already guarantees uniqueness
  AND no transformation or enforced expectation is needed beyond a straight
  passthrough select. Rare in practice, since Silver Landing almost always
  adds provenance metadata.

### Naming Conventions
- schema: `silver_landing_{source_system}`
- tables or models: `{datasource}` - the entity's logical name only, e.g.
  `customers`, never the Bronze Publish object's SCD-suffixed name (e.g.
  not `customers_scd2`), regardless of which SCD variant precedence
  currently selects. See **Discussion point** below.

> **Discussion point (resolved 2026-09-25)** — this line originally read
> "same name as bronze publish", which was ambiguous: literally the same
> object name including its SCD suffix, or just the same logical entity
> name? Resolved to the logical-name-only reading above; full rationale
> and alternative considered recorded in
> [`docs/decision-register.md`](../decision-register.md#2026-09-25-silver-landing-table-naming-keep-or-drop-the-bronze-scd-suffix).

### Standards applied
- If SCD columns from Bronze Publish are not descriptive enough, e.g., `_START_AT` and `_END_AT` apply a column rename `scd_valid_from_timestamp` and `scd_valid_to_timestamp`.
- Add a `is_current` column to SCD2 is not available using `case when _END_AT is null then true else false end` logic.
- Silver Landing does not generate surrogate keys; that is deferred to a
  later Silver sub-layer. If Bronze Publish already provides one, it must
  remain the first column of any object in this layer
- natural keys must come right after the surrogate key, when avaiable, e.g., mdp_prd.`bronze_airroi_publish.market_metrics_all_scd2` has five columns as natural keys `_country, _region, _locality, _district, date` and they must be right after the surrogate key if available. if not they would be the first five columns of the object.
- comments on natural key columns must clearly mention it.
- `ingested_timestamp` is never stamped by Silver Landing; if the Bronze
  Publish source object already carries one (propagated from `_raw`), pass
  it through unchanged. If it doesn't (not yet retrofitted for that
  source, per `NAMING.md`), the column is simply absent — Silver Landing
  does not backfill it.
- `transformed_timestamp` is stamped with `current_timestamp()` at this
  layer's own refresh, on every table regardless of whether Bronze already
  had one — it reflects the most recent transformation, not the first.

### Orchestration (forward-looking)
Silver Normalised (`silver_normalised_{source}`) will be a second,
source-aligned pipeline per source, reading from that source's Silver
Landing tables. Once it exists, a per-source job chains the two via
`pipeline_task` + `depends_on` (the same dependency pattern already used
for notebook tasks in `verify_unspsc_pattern.job.yml` and
`neon_scd2_merge_sql.job.yml`), so Normalised never reads a stale/partial
Landing refresh. No job exists yet — this section just reserves the naming
convention:
- Landing pipeline: `silver--landing--{source}--${bundle.target}`
- Normalised pipeline (future): `silver--normalised--{source}--${bundle.target}`
- Orchestrating job (future): `silver--{source}--${bundle.target}`, tasks
  `landing` then `normalised` (`depends_on: [landing]`)

### Agent instructions
Look at the definition of this layer, propose changes based on the sources to be exposed and update the content on this sections if changes made are permanent and applied to future iterations.
