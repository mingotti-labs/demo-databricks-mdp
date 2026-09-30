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
- Silver Landing does not generate surrogate keys; that is deferred beyond
  Silver Normalised (Domain or later). If Bronze Publish already provides
  one, it must remain the first column of any object in this layer
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

## Silver Normalised
### Purpose
Restructure the Silver Landing tables of one source at a time into third
normal form, and extract every coded attribute into its own normalised
entity, without changing any value.

Judgement (which columns share a domain, which attributes depend on
which) is applied once per source at design time, by an agent proposing a
reviewed per-source **normalised spec**; one generic pipeline executes that
spec deterministically at run time. How a source moves through this layer
is not repeated here: see [CONTRIBUTING.md](../../CONTRIBUTING.md) for the
two-PR flow and [Adding a source](../normalised-spec/README.md#adding-a-source)
for the Normalised-specific steps.

### Terminology
"Reference" is deliberately avoided: in this platform it reads as
authoritative, and nothing in this layer is.

| Term | Meaning | Example |
| --- | --- | --- |
| Normalised entity | Any entity table in `silver_normalised_{source}` | `customers`, `country` |
| Base entity | Restructured from one Landing table; keeps that table's name, grain and row count | `customers`, `charity_register` |
| Bridge entity | One row per element of a repeating group in a Landing table (N2) | `charity_register_operating_country` |
| Extracted entity | Built from the distinct values of one or more Landing columns in the same domain | `country`, `order_status` |
| Authoritative dataset | A trusted list that values are matched to; never produced by this layer | ISO 3166 country codes |

### Characteristics
- Source-aligned: reads only `silver_landing_{source}`; no cross-source joins
- Structural change, not semantic change: values are never corrected or mapped
- Deterministic: the same Landing input always gives the same rows
- Natural keys only; surrogate keys deferred beyond this layer (Domain or later)
- Base entities keep row-count parity with Landing (together with their
  `{entity}_quarantine`, if any); bridges match the Landing element count;
  extracted entities keep value completeness (every non-null Landing value
  in a member column has a row)
- Every entity tagged in Unity Catalog: `mdp_layer = silver_normalised`,
  `mdp_source_system = {source}`, `mdp_entity_kind = base | bridge | extracted`
- Precondition: the source's Landing tables carry `ingested_timestamp`
  (see [NAMING.md](../../NAMING.md#platform-added-timestamp-columns))

### What fits here
- 1NF/2NF/3NF splits and bridge entities for multi-valued attributes
- Extracted entities and the per-source `value_lineage` table
- The `rdm_proposed_match_key` hint column on extracted entities
- `{entity}_quarantine` for dependency exceptions under a declared tolerance

### What does NOT fit here
- Mapping values to authoritative datasets (that is rdm, consumed later in
  Domain — see [rdm](../component/rdm/README.md))
- Reading anything from rdm: rdm depends on this layer, never the reverse
- Joins across sources, conformed entities, business rules
- LLM calls at pipeline run time

### Materialisation when Databricks Native
Materialized Views, since every input is an upsert-maintained Landing MV.
One generic pipeline, instanced once per source under the names reserved
in Silver Landing's Orchestration section above.

### Normalisation rules
Binding for every source. The agent applies them when proposing a
normalised spec; the reviewer checks against them. N1–N6 are classic 3NF;
N7–N10 are specific to this platform.

| # | Rule | Detect by | Produces |
| --- | --- | --- | --- |
| N1 | No generated surrogate keys: every entity is identified by its natural key, first column(s), with Landing's natural-key comment convention. A surrogate key already carried by Landing is passed through as the first column | Landing natural keys | Surrogate keys stay deferred beyond this layer |
| N2 | Repeating groups become bridge entities (1NF) | Delimited lists (`AU;NZ;FJ`), numbered or flag column families (`operates_in_nsw`, `operates_in_vic`…) | `{parent}_{attribute}` bridge |
| N3 | Attributes depending on part of a composite key move out (2NF) | Dependency check on composite-key tables | New entity at the partial key |
| N4 | Attributes depending on a non-key attribute move out (3NF), **only when the dependency holds with zero exceptions** | Does each `locality` always come with the same `region`? | New entity keyed by `locality`; parent keeps `locality` as FK |
| N5 | Hierarchies become one entity per level, each pointing to its parent level | Chained dependencies, e.g. `_locality → _region → _country` | `country` ← `region` ← `locality` |
| N6 | SCD2 history stays on the base entity that owns it; bridges inherit their parent row's validity; extracted entities are not versioned | Landing `scd_valid_from/to_timestamp`, `is_current` | Validity columns only on base entities |
| N7 | Every coded attribute becomes an extracted entity named after its domain, collecting values from every table and column in that domain and from all SCD2 versions, even when only one column has it | Column-name semantics + value overlap + low cardinality | One entity per domain, its attributes in 3NF |
| N8 | Raw values kept exactly; `rdm_proposed_match_key` groups obvious variants with fixed rules: trim, collapse inner whitespace, uppercase, strip accents. Never used inside Silver | Always | `AUSTRALIA`, `Australia`, `AuStRaLiA` = 3 rows, 1 match key; `São Paulo` → `SAO PAULO` |
| N9 | Every extracted value records where it was seen | Always | `value_lineage` |
| N10 | Referencing columns stay in the base entity as FKs; attributes that depended on them move to the extracted entity | Always | `country_name` lives only in `country` |

**Why zero exceptions in N4.** AirROI, where each locality should have one
region:

| locality | region | rows |
| --- | --- | --- |
| Urubici | Santa Catarina | 9,997 |
| Urubici | Santa Catrina | 3 |

The check fails, so `locality` is not split out and `region` stays on the
base entity; nothing is lost. Splitting anyway would force Silver to pick
the "winning" region, a business decision. The exception is a spelling
variant, exactly what rdm resolves later. A tolerance is allowed only case
by case, declared in the normalised spec with the reason in the source
change's `design.md`; the exception rows then go to `{entity}_quarantine`,
never silently dropped.

A domain is decided by meaning, not column name: `billing_country` and
`ship_to_ctry` both belong to `country`. The normalised spec lists every
domain's member columns explicitly, so it is a reviewed decision, not a
runtime heuristic.

### Standards applied
- Table naming per [NAMING.md](../../NAMING.md#silver-normalised-tables)
- `transformed_timestamp` stamped on every table at this layer's refresh
- `ingested_timestamp`: base and bridge entities pass it through from
  their Landing row; extracted entities and `value_lineage` carry the
  `max()` of the Landing rows they aggregate
- Every Landing column a source's normalised spec reads is either used or
  listed in its `ignored_columns`; a new Landing column fails the drift
  check until the spec is updated

### Agent instructions — Silver Normalised
When proposing a source for this layer, follow
[`docs/templates/silver-normalised-propose.prompt.md`](../templates/silver-normalised-propose.prompt.md)
(also loaded by the `silver-normalised-propose` skill). Rules N1–N10 are
binding, and the source's normalised spec must validate against the
normalised spec schema,
[`docs/normalised-spec/schema.json`](../normalised-spec/schema.json).
