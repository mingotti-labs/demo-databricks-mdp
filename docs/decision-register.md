# Decision Register

A durable log of architecture/convention decisions that were genuinely
debated and could plausibly have gone another way. Not a changelog of
every change — only decisions worth preserving the "why not the
alternative" for. Newest entries at the top.

---

The eighteen 2026-09-30 entries below come from
`phase4c-silver-normalised-design-time`; its design.md has the full
reasoning. They share one **Affected** set unless stated:
`docs/medallion/silver.md` ("Silver Normalised"), `NAMING.md`,
`docs/normalised-spec/`, `docs/templates/`.

---

## 2026-09-30: Silver Normalised — change IDs renumbered

**Context**: The design came from a planning session that named its
changes `phase4b1`/`phase4b2`.

**Discussion**: `phase4b` is already `phase4b-silver-landing-iso-geonames`,
so `4b1` would read as a child of an unrelated change.

**Decision**: `phase4c` (design time), `phase4d` (run time), `phase4e`
(acnc, first source), then one letter per source.

**Affected**: openspec change IDs only.

---

## 2026-09-30: Silver Normalised — drift check in verification, not CI

**Context**: A normalised spec must account for every Landing column.

**Discussion**: CI has no Databricks access, so it cannot see Landing's
live columns; it can only check a spec's format.

**Decision**: CI validates every spec against `schema.json`; the drift
check (every Landing column used or in `ignored_columns`) runs in the
verification job, against the deployed tables.

---

## 2026-09-30: Silver Normalised — two-pass profiling

**Context**: N4 needs a zero-exception dependency check per candidate pair.

**Discussion**: Checking all column pairs is quadratic in column count —
too heavy for Free Edition's shared serverless pool on a wide table.

**Decision**: Pass 1 profiles columns and value overlaps; the agent picks
candidate pairs from it; pass 2 checks only those.

---

## 2026-09-30: Silver Normalised — profile returned as run output

**Context**: The planning draft had the profiling job write JSON to a UC
volume.

**Discussion**: Volumes are owned by `demo-databricks-iac`, so that would
add a Terraform change and a cross-repo dependency, while the durable copy
is `profile.json` in the source's openspec change anyway.

**Decision**: The notebook returns one JSON document via
`dbutils.notebook.exit`; the agent fetches it with
`databricks jobs get-run-output`. If a source's profile ever exceeds the
run-output size limit, a volume becomes its own change.

---

## 2026-09-30: Silver Normalised — profiling job built at design time

**Context**: The planning draft placed the profiling job in the run-time
framework change, with ad-hoc SQL until then.

**Discussion**: Profiling only feeds the design-time agent. Building it
later would give the first source's evidence a different shape from every
later source's.

**Decision**: The framework is split by design time (`phase4c`: rules,
spec format, agent, profiling job) vs run time (`phase4d`: generic
pipeline, verification, CI), not by docs vs code.

**Affected**: also `src/layers/silver/normalised/profile.py`,
`resources/jobs/profile_silver_normalised.job.yml`.

---

## 2026-09-30: Silver Normalised — plain tags now, governed tags deferred

**Context**: rdm must find extracted entities across sources.

**Discussion**: Plain Unity Catalog tags are enough for discovery.
Governed tags (tag policies enforcing allowed values) would enforce them,
but were not assessed for this workspace.

**Decision**: Every entity carries plain tags `mdp_layer`,
`mdp_source_system`, `mdp_entity_kind = base | bridge | extracted`.
Governed tags go to the `demo-databricks-planning` roadmap backlog, to
discuss once Silver Normalised is finalised.

---

## 2026-09-30: Silver Normalised — rdm consumes it, never the reverse

**Context**: Value matching needs both Silver Normalised's values and
rdm's decisions.

**Discussion**: A two-way dependency would make Silver's output depend on
steward activity and break determinism.

**Decision**: rdm reads Silver Normalised; Silver Normalised never reads
rdm, and the normalised spec has no `rdm` block. Approved matches reach
the data in Domain.

**Affected**: also `docs/component/rdm/README.md`.

---

## 2026-09-30: Silver Normalised — no first/last-seen columns in v0.1

**Context**: The planning draft had `first_seen_timestamp` /
`last_seen_timestamp` on extracted entities, from SCD2 validity.

**Discussion**: No reliable source exists today: `ingested_timestamp` is
restamped on every `_raw` MV run, and SCD1-sourced Landing tables (neon
orders, clickstream events) have no validity columns. rdm does not need
them.

**Decision**: Dropped from v0.1; on the planning roadmap backlog, to add
with a real definition when a consumer needs them.

---

## 2026-09-30: Silver Normalised — `ingested_timestamp` precondition and `max()`

**Context**: `ingested_timestamp` exists only on airroi, iso and geonames;
extracted entities aggregate many Landing rows.

**Discussion**: Handling an absent column in the generic pipeline adds a
code path to every source; retrofitting all five older sources now
touches sources that may never be normalised. For aggregation, `min()`
would look like "first ingested" without being that, since `_raw` MVs
restamp the column.

**Decision**: Landing must carry `ingested_timestamp` before a source is
normalised; a source lacking it is retrofitted at bronze in its own change,
just in time. Base and bridge entities pass it through; extracted entities
and `value_lineage` carry `max()`.

---

## 2026-09-30: Silver Normalised — bridges as their own entity kind

**Context**: A bridge (one row per list element) cannot keep row-count
parity with its Landing table.

**Discussion**: Treating it as a base entity would make the parity check
fail by design.

**Decision**: Bridge is a third entity kind (`mdp_entity_kind = bridge`),
checked by element count instead of row parity, and declared in its own
`bridge_entities` block of the normalised spec, one block per entity kind.
Declaring bridges as `base_entities` entries marked by `explode`/`unpivot`
was rejected: it mixes two kinds in one block and needs conditional
validation. If bridges prove unnecessary, the block is removed (a major
version bump).

---

## 2026-09-30: Silver Normalised — zero-exception dependency splits

**Context**: N3/N4 move attributes out when they depend on something other
than the whole key.

**Discussion**: With exceptions (e.g. `Urubici` → `Santa Catarina` 9,997
rows, `Santa Catrina` 3 rows), splitting forces Silver to pick a winning
value — a business decision, and exactly what rdm resolves.

**Decision**: Split only at zero exceptions. A per-case
`dependency_tolerance` is allowed, with its reason in the source change's
design.md; the exception rows go to `{entity}_quarantine`, whose NAMING.md
definition is widened beyond bronze.

---

## 2026-09-30: Silver Normalised — one `value_lineage` table per source

**Context**: The same value can appear in several columns with different
meanings (`AU` as a phone prefix vs an address country).

**Discussion**: One lineage table per extracted entity would multiply
tables for no gain.

**Decision**: One `value_lineage` per source schema, recording entity,
value, source table, source column and row count, for people and impact
analysis.

---

## 2026-09-30: Silver Normalised — `rdm_proposed_match_key` hint column

**Context**: `AUSTRALIA`, `Australia` and `AuStRaLiA` should be one rdm
decision, but Silver must not change values.

**Discussion**: Computing the grouping in rdm would duplicate it per
consumer; computing it in Silver risks it being used as a correction.

**Decision**: A hint column on extracted entities, from fixed rules only
(trim, collapse inner whitespace, uppercase, strip accents), prefixed
`rdm_` and never used inside Silver.

---

## 2026-09-30: Silver Normalised — single-table coded columns are extracted

**Context**: Some coded attributes appear in only one table of a source.

**Discussion**: Leaving them inline would hide them from rdm.

**Decision**: Every coded attribute becomes an extracted entity (N7), even
with one member column; these feed rdm's "curate, then match" use case
when no authoritative dataset exists.

---

## 2026-09-30: Silver Normalised — no generated surrogate keys

**Context**: Silver Landing deferred surrogate keys to "a later Silver
sub-layer", which read as Normalised.

**Discussion**: rdm's crosswalk keys on (`source_system`, `entity`,
`value`); a generated key would add drift risk with no consumer.

**Decision**: Natural keys only (N1); a surrogate key already carried by
Landing is passed through. Deferral reworded to "beyond Silver Normalised
(Domain or later)".

---

## 2026-09-30: Silver Normalised — table naming

**Context**: The planning draft renamed a base entity (`charity_register`
→ `charity`) and mixed plural base with singular extracted names.

**Discussion**: Renaming base entities breaks one-to-one traceability back
to Landing.

**Decision**: Base entities keep the Landing table name; extracted
entities use the singular domain name only (the schema carries the
source); bridges are `{parent}_{attribute}`.

---

## 2026-09-30: Silver Normalised — terminology

**Context**: The layer needs names for its three kinds of table and for
the trusted lists values are matched to.

**Discussion**: "Reference" reads as authoritative in this platform, and
nothing in this layer is.

**Decision**: Normalised entity (any), base entity (from one Landing
table), bridge entity (repeating group), extracted entity (domain values);
"authoritative dataset" for trusted lists such as ISO 3166.

---

## 2026-09-30: Silver Normalised — gen AI at design time only

**Context**: Normalisation needs judgement (domains, dependencies) that
Silver Landing never did.

**Discussion**: Rules in markdown only leaves each source as bespoke code,
enforced by review alone. `ai_query` in the pipeline is non-deterministic,
costs per refresh, and is hard to verify or audit.

**Decision**: An agent profiles Landing and proposes a per-source
normalised spec, reviewed in the propose PR; one generic pipeline executes
any spec deterministically. No LLM runs at pipeline run time.

---

## 2026-09-25: Silver Landing provenance timestamp column name

**Context**: `docs/medallion/silver.md`'s original "Provenance metadata"
line (written before `phase4a-silver-landing`) listed `ingested_timestamp`
as a column Silver Landing adds. `NAMING.md`'s "Platform-added timestamp
columns" section already defines `ingested_timestamp` as stamped exactly
once, at `_raw`, and never changed downstream — a genuine name collision
only visible once both docs were read together (found while preparing to
commit `phase4a-silver-landing`, not caught during initial drafting).

**Discussion**: Silver Landing is a transformation step over Bronze
Publish, not an ingestion step — restamping `ingested_timestamp` there
would corrupt its established, immutable meaning. `NAMING.md` already had
a column for exactly this situation, `transformed_timestamp`, but scoped
its description to bronze's own `_scd1`/`_scd2` layer specifically.

**Decision**: Silver Landing stamps `transformed_timestamp`
(`current_timestamp()` at its own refresh) instead of `ingested_timestamp`.
`ingested_timestamp` is propagated unchanged when the Bronze Publish source
already carries one (currently only AirROI's two entities), and left
absent otherwise — Silver Landing does not backfill it. `NAMING.md`'s
`transformed_timestamp` description is generalized from "the bronze
`_scd1`/`_scd2` layer" to "any transformation layer downstream of `_raw`,"
since this is no longer a bronze-only concept.

**Affected**: `NAMING.md` ("Platform-added timestamp columns"),
`docs/medallion/silver.md` (Provenance metadata, Standards applied),
`openspec/changes/phase4a-silver-landing/` (spec, design, proposal, tasks
corrected to match).

---

## 2026-09-25: Silver Landing table naming — keep or drop the Bronze SCD suffix

**Context**: While proposing Silver Landing (`phase4a-silver-landing`),
`docs/medallion/silver.md`'s naming convention read "tables or models:
`{datasource}` - same name as bronze publish". This was ambiguous: does
"same name" mean the literal Bronze Publish object name including its SCD
suffix (e.g. `customers_scd2`), or the entity's logical datasource name
only (e.g. `customers`)?

**Discussion**:
- **Keep the full name** (`customers_scd2`): directly traceable to which
  Bronze Publish object and SCD strategy fed the Silver table — useful for
  debugging and lineage, and arguably the more literal reading of the
  original convention text.
- **Drop the suffix** (`customers`): decouples Silver Landing consumers
  from Bronze Publish's internal SCD variant choice. Bronze Publish was
  deliberately used to test multiple ingestion/SCD patterns per source
  (e.g. neon has both Python and SQL SCD1/SCD2 variants for the same
  entities). Which variant actually feeds Silver is governed by the
  SCD2 > SCD1 > SCD0 precedence rule, which could select a different
  Bronze object for the same entity in the future (e.g. if a real SCD2 is
  later built for `orders`, currently SCD1-only) without the entity itself
  changing. Keeping the suffix would force a rename (or leave a stale
  suffix pointing at the wrong variant) when that happens; dropping it
  means the same Silver table name keeps working.

**Decision**: Drop the suffix. Silver Landing table names use the entity's
logical datasource name only (e.g. `silver_landing_neon.customers`, not
`silver_landing_neon.customers_scd2`), regardless of which Bronze Publish
SCD variant is currently selected.

**Affected**: `docs/medallion/silver.md` (Naming Conventions section);
`openspec/changes/phase4a-silver-landing/` (spec, design, and tasks were
authored with this decision already applied).
