# Decision Register

A durable log of architecture/convention decisions that were genuinely
debated and could plausibly have gone another way. Not a changelog of
every change — only decisions worth preserving the "why not the
alternative" for. Newest entries at the top.

---

The ten 2026-10-01 entries below come from
`phase4e-silver-normalised-acnc`; its design.md has the full reasoning.
**Affected** unless stated: `src/layers/silver/normalised/`,
`src/common/normalised_spec.py`, `docs/medallion/silver.md`,
`docs/normalised-spec/README.md`, `docs/templates/silver-normalised-propose.prompt.md`.

---

## 2026-10-01: acnc — no address hierarchy

**Context**: Postcode, Town_City, State and Country looked like a candidate hierarchy; profiled on acnc's full ~66k-row dataset in `dev` (cross-checked read-only against `prd`), every pairwise dependency among them breaks (10 to 1,723 violating values).

**Discussion**: A tolerance with quarantine was considered; rejected, since the violations are hundreds of values, mostly spelling variants (`NSW`/`nsw`) plus genuine cross-border postcodes (`0872`, `2620`) — rdm's job, not Silver's.

**Decision**: All four stay independent extracted entities, each a foreign key on `charity_register`; no parent/child relationship among them.

---

## 2026-10-01: acnc — flag-family elements are column names, not values

**Context**: The 8 `Operates_in_*` flags look like they belong to the same domain as `State`.

**Discussion**: Merging them would need a schema attribute to strip the `Operates_in_` prefix before the element becomes the extracted value; v0.2 has none.

**Decision**: A separate `operating_state` extracted entity holds the raw column names (`Operates_in_NSW`…). A prefix-strip attribute is a candidate for a later minor bump if a second source needs it.

---

## 2026-10-01: acnc — kept on the base entity, not bridged

**Context**: `Address_Line_1..3`, `Other_Organisation_Names`, `PBI` and `HPC` could each look like repeating-group candidates.

**Discussion**: Address lines are ordered parts of one address, not a set; `Other_Organisation_Names` mixes `,`/`;` delimiters and contains names with embedded commas, so splitting would corrupt values; `PBI`/`HPC` are two independent flags, not a family.

**Decision**: All four stay as plain columns on `charity_register`.

---

## 2026-10-01: Silver Normalised — schema v0.2, `unpivot.columns`

**Context**: acnc's purpose (12 columns) and beneficiary (29 columns) flag families share no name prefix `columns_like` could select.

**Discussion**: Planned in `phase4c`'s findings as the first expected minor bump.

**Decision**: `unpivot` accepts `columns` (an explicit list) as an alternative to `columns_like`; the pipeline, drift check and verification read either.

---

## 2026-10-01: Silver Normalised — null is not a value when resolving a parent

**Context**: Profiling's dependency check already ignores nulls (`count(DISTINCT dependent)`); the pipeline's `groupBy` did not, so a value with one recorded parent and some blank occurrences got two rows instead of one, a mismatch found while reviewing acnc's postcode→state evidence (though acnc's spec ends up with no parent relationships at all).

**Discussion**: The alternative was to make profiling count null as a value instead, so a blank parent would count as a real exception and the dependency would never split; rejected as the less natural reading — a blank is missing information, not a different value.

**Decision**: A value recorded with exactly one distinct non-null parent gets that parent on every row, including its null-parent occurrences. A value recorded with two or more distinct non-null parents is left untouched, so the genuine conflict still produces one row per parent, caught by verification's extracted-key uniqueness check.

---

## 2026-10-01: Silver Normalised — `ingested_timestamp` verified on current rows only

**Context**: Auto CDC never rewrites a closed SCD2 version, so a version closed before a source's retrofit keeps a null `ingested_timestamp` forever (acnc has 10 such rows in `dev`).

**Discussion**: Retrofitting every source's full history was rejected (touches sources that may never be normalised); so was treating the nulls as a verification failure (would block every retrofitted source indefinitely).

**Decision**: Verification checks `ingested_timestamp` non-null only on current rows of SCD2 base/bridge/quarantine tables (and on every row elsewhere); `transformed_timestamp` is still checked everywhere. An extracted/`value_lineage` row aggregated only from pre-retrofit history can legitimately get a null `max()` — rare, accepted, not checked.

---

## 2026-10-01: Silver Normalised — dependency evidence from full data for row-limited sources

**Context**: acnc's `dev`/`tst` sampled 500 of ~66k rows; Postcode → State had 0 violations on the sample and 157 on the full data (and in `prd`, cross-checked).

**Discussion**: Proposing a split on sampled evidence risks a deploy-time failure in `prd`, found far later than design-time review.

**Decision**: A row-limited source's dependency checks (N3–N5) must come from the full dataset — lift the `dev` limit for the change if the source allows it (acnc: free CKAN API), otherwise run the same checks read-only against `prd`.

---

## 2026-10-01: acnc's `ingested_timestamp` retrofit folded into its Silver Normalised change

**Context**: `phase4c`/`phase4d` assumed a source's bronze retrofit is always its own change, ahead of normalising it.

**Discussion**: A separate change is cleaner to review per layer, but costs two more PRs and makes `phase4e`'s profiling wait on it; the user chose to fold it in.

**Decision**: The retrofit is the normalising change's first implementation task group, verified in `dev` before the Normalised pipeline is deployed. The README and prompt template's step 0 now allow either shape.

---

## 2026-10-01: acnc's `dev` loads the full dataset going forward

**Context**: The 500-row sample hid real conflicts from profiling (see above); acnc's CKAN API pull is free.

**Discussion**: Keeping the sample and relying only on the `prd` cross-check was considered; rejected — every later acnc change (not just this one) would otherwise profile and verify against unrepresentative `dev` data.

**Decision**: `acnc_row_limit` is unset for `dev` as well as `prd`; only `tst` keeps the 500-row sample. **Affected**: `databricks.yml`.

---

## 2026-10-01: Dev ownership check added to the per-source workflow

**Context**: acnc's `silver_landing_acnc` (and, found later, `neon`'s dev tables) were still owned by a human identity, not the CI/CD service principal, the same class of issue `phase4d` found for airroi.

**Discussion**: A repo-wide sweep was considered and rejected (cost without an immediate need; most sources aren't scheduled for normalising soon).

**Decision**: Each source's Silver Normalised change checks and fixes its own `dev` ownership at step 0, just in time, rather than a sweep. **Affected**: `docs/normalised-spec/README.md`, the prompt template.

---

## 2026-09-30: airroi as the first source, inside the framework change

**Context**: The run-time framework needed a real source to prove itself; acnc, the planned pilot, still needs its `ingested_timestamp` retrofit.

**Discussion**: A synthetic fixture needs a throwaway schema; deferring every real run to acnc leaves the framework unverified until 4e.

**Decision**: airroi, whose Landing already carries `ingested_timestamp`, is profiled and normalised inside `phase4d`. Bridges and tolerances get their first real run in acnc.

---

## 2026-09-30: Silver Normalised — pure spec logic apart from Spark transforms

**Context**: Spec rules need unit tests; the repo's tests have no Spark or Java.

**Discussion**: One module would make every test need a Spark session.

**Decision**: `src/common/normalised_spec.py` (pure Python, pytest) and `src/layers/silver/normalised/transforms.py` (Spark, verified on real runs).

---

## 2026-09-30: Silver Normalised — cross-reference checks in code, schema stays structural

**Context**: Some spec rules (a bridge's parent exists, a parent chain has no cycle) span several blocks.

**Discussion**: Expressing them in JSON Schema is possible only partly and hard to read.

**Decision**: `load_spec` checks them; the pipeline calls it before defining any table, and the tests cover one failing case per rule.

---

## 2026-09-30: Silver Normalised — platform columns handled by the framework

**Context**: Validity, provenance and timestamp columns are on every Landing table.

**Discussion**: Listing them in every spec repeats the same seven columns per entity.

**Decision**: The pipeline carries them; specs never list them and the drift check never counts them.

---

## 2026-09-30: Silver Normalised — group, don't pick, on extracted entities

**Context**: A dependency can break in later data (a second `Prado` in another region).

**Discussion**: `max()`/`first()` would keep one row per value but silently choose a winner.

**Decision**: Rows are grouped by value, parent and attributes; a break shows up as a duplicate key and fails verification.

---

## 2026-09-30: Silver Normalised — tags by a post-refresh step, keys without dots

**Context**: `@dp.materialized_view` has no tags parameter, and Unity Catalog rejects `.` in tag keys.

**Discussion**: Tagging in Terraform would need the tables to exist before the pipeline creates them.

**Decision**: A `tag` task runs `ALTER MATERIALIZED VIEW … SET TAGS` after every refresh; keys are `mdp_layer`, `mdp_source_system`, `mdp_entity_kind`. Table ownership is enough; no `APPLY TAG` grant.

---

## 2026-09-30: Silver Normalised — match key as a UDF shipped by value

**Context**: Workers lack the driver's `sys.path` entry for `src/`, as acnc's connector showed.

**Discussion**: An inline copy in the pipeline would run code the tests don't cover.

**Decision**: `cloudpickle.register_pickle_by_value` ships the tested `match_key`; confirmed on serverless (`Vitória da Conquista` → `VITORIA DA CONQUISTA`).

---

## 2026-09-30: Silver Normalised — N3 never splits a natural-key column

**Context**: airroi's `_region`/`_country` depend on `_locality`, part of its key.

**Discussion**: Strict 2NF would drop them from the key, making it depend on locality names being globally unique.

**Decision**: Landing's natural key stays whole (N1); dependencies among key columns live in the extracted hierarchy (N5).

---

## 2026-09-30: airroi — distribution metrics stay as MAP columns

**Context**: `market_metrics_all` has seven MAPs of fixed keys (`avg`, `p25` … `p90`).

**Discussion**: Flattening to columns is arguably 1NF but needs a schema attribute v0.1 lacks; a bridge fits repeating groups, not fixed keys.

**Decision**: Kept as MAPs; a `flatten` attribute is a candidate minor bump.

---

## 2026-09-30: Silver Normalised — pytest in PR CI

**Context**: The spec logic now has unit tests; CI ran none.

**Discussion**: Running them only locally lets a broken rule reach `main`.

**Decision**: A credential-free `normalised-specs` job validates specs against the schema and runs `uv run pytest`.

---

## 2026-09-30: Pipelines never glob `src/common/**`

**Context**: Twelve pipelines listed `src/common/**` in `libraries`, a phase3c leftover from before the `sys.path` import fix.

**Discussion**: Keeping it is harmless only while no `common/` module imports a sibling.

**Decision**: Removed (#47) after validate-only runs on 11 of the 12 pipelines; `common/` is imported via `sys.path` only.

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
