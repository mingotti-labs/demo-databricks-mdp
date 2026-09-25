# Decision Register

A durable log of architecture/convention decisions that were genuinely
debated and could plausibly have gone another way. Not a changelog of
every change — only decisions worth preserving the "why not the
alternative" for. Newest entries at the top.

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
