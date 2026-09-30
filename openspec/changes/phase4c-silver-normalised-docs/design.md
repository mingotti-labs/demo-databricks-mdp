## Context

See proposal.md for why. Adapted from a design proposal agreed in a
separate planning session (2026-09-30), reconciled with this repo's
`silver.md`, `NAMING.md` and `docs/registers/data-sources.md` before
writing; the reconciliation decisions are listed under Decisions.

Current state:
- Silver Landing exists for all eight sources (`phase4a`, `phase4b`), one
  materialized view per Bronze Publish entity, in
  `src/layers/silver/landing/{source}/`, with pipelines in
  `resources/pipelines/silver_landing_{source}.pipeline.yml`.
- `silver.md` already reserves Silver Normalised's pipeline and job names
  (`silver--normalised--{source}--${bundle.target}`, orchestrated after
  Landing by `silver--{source}--${bundle.target}`).
- `ingested_timestamp` is only present on airroi, iso and geonames; it was
  introduced at `phase3h` and never retrofitted to neon, clickstream,
  ungm, acnc or nsw_spatial.

Requirements are in `specs/silver-normalised/spec.md`; this document
covers the approach, formats, artefacts and decisions behind them.

## Goals / Non-Goals

**Goals:**
- Define the layer (rules N1–N10) precisely enough that an agent can
  propose a source's normalised spec and a reviewer can check it.
- Define the normalised spec format (v0.1) and the design-time agent's
  instructions, in one place each.
- Provide the standard profiling job, so the agent's evidence has one
  fixed shape from the first source onwards.
- Let the agent be tried on acnc before the generic pipeline exists.

**Non-Goals:**
- The generic pipeline, verification and CI step
  (`phase4d-silver-normalised-framework`).
- Governed tags (tag policies); plain Unity Catalog tags only. Deferred to
  the `demo-databricks-planning` roadmap backlog.
- Normalising any source (`phase4e-silver-normalised-acnc` onwards).
- Building rdm, or deciding its internals beyond the interface below.
- Retrofitting `ingested_timestamp` to older sources.

## Approach: gen AI at design time, deterministic rules at run time

| Option | What it looks like | Verdict |
| --- | --- | --- |
| Rules in md only | `silver.md` lists the rules; a person or agent hand-writes each source's pipeline | Works, but each source is bespoke code and the rules are only enforced by review |
| Gen AI in the pipeline | `ai_query` decides entities and dedupes values on each refresh | Rejected: non-deterministic output, keys can drift between runs, cost per refresh, hard to verify or audit |
| **Hybrid (chosen)** | md rules + an agent prompt profile Landing and emit a per-source YAML normalised spec; one generic pipeline executes any spec | Judgement is captured once, reviewed in the propose PR, and replayed deterministically |

This fits the repo's existing SDLC: the propose PR (Opus) produces the
spec, the implement PR (Sonnet) mostly deploys it. The one place gen AI
runs continuously, matching `AuStRaLiA` to `AU`, lives in rdm, with a
human approving matches.

Flow: Silver Landing → profiling (design time) → agent proposes normalised
spec + `design.md` → human review in PR 1 → generic pipeline executes the
spec (run time) → tagged extracted entities → rdm matches and a steward
approves → only approved crosswalk rows reach Domain.

## Layer definition

Goes into `docs/medallion/silver.md`, in the same shape as the Silver
Landing section. How a source moves through the layer is not repeated
there: `silver.md` links to CONTRIBUTING.md for the two-PR flow and to
`docs/normalised-spec/README.md` ("Adding a source") for the
Normalised-specific steps.

**Purpose.** Restructure the Silver Landing tables of one source at a time
into third normal form, and extract every coded attribute into its own
normalised entity.

**Terminology.** "Reference" is avoided: in this platform it reads as
authoritative, and nothing in this layer is.

| Term | Meaning | Example |
| --- | --- | --- |
| Normalised entity | Any entity table in `silver_normalised_{source}` | `customers`, `country` |
| Base entity | Restructured from one Landing table; keeps that table's name, grain and row count | `customers`, `charity_register` |
| Bridge entity | One row per element of a repeating group in a Landing table (N2) | `charity_register_operating_country` |
| Extracted entity | Built from the distinct values of one or more Landing columns in the same domain | `country`, `order_status` |
| Authoritative dataset | A trusted list that values are matched to; never produced by this layer | ISO 3166 country codes |

**Characteristics**
- Source-aligned: reads only `silver_landing_{source}`; no cross-source joins
- Structural change, not semantic change: values are never corrected or mapped
- Deterministic: the same Landing input always gives the same rows
- Natural keys only; surrogate keys deferred beyond this layer (Domain or later)
- Base entities keep row-count parity with Landing (plus quarantine);
  bridges match the element count; extracted entities keep value completeness
- Every entity tagged `mdp.layer = silver_normalised`,
  `mdp.source_system = {source}`, `mdp.entity_kind = base | bridge | extracted`

**What fits here**
- 1NF/2NF/3NF splits and bridge entities for multi-valued attributes
- Extracted entities and the per-source `value_lineage` table
- The `rdm_proposed_match_key` hint column, computed by fixed rules
- `{entity}_quarantine` for dependency exceptions under a declared tolerance

**What does NOT fit here**
- Mapping values to authoritative datasets (rdm, consumed later in Domain)
- Reading anything from rdm: rdm depends on this layer, never the reverse
- Joins across sources, conformed entities, business rules
- LLM calls at pipeline run time

**Materialisation.** Materialized views, since every input is an
upsert-maintained Landing MV. One generic pipeline source file, instanced
once per source as its own pipeline resource, using the names `silver.md`
already reserves.

**Agent instructions — Silver Normalised** (labelled subsection in
`silver.md`): when proposing a source, follow
`docs/templates/silver-normalised-propose.prompt.md`. Rules N1–N10 are
binding, and the source's normalised spec must validate against
`docs/normalised-spec/schema.json`.

## Normalisation rules

Go into `silver.md`. The agent applies them when proposing; the reviewer
checks against them. N1–N6 are classic 3NF; N7–N10 are the twist.

| # | Rule | Detect by | Produces |
| --- | --- | --- | --- |
| N1 | No generated surrogate keys: every entity is identified by its natural key, first column(s), with Landing's key-comment convention. A surrogate key already carried by Landing is passed through as the first column | Landing natural keys | Surrogate keys stay deferred beyond this layer |
| N2 | Repeating groups become bridge entities (1NF) | Delimited lists (`AU;NZ;FJ`), numbered or flag column families (`operates_in_nsw`, `operates_in_vic`…) | `{parent}_{attribute}` bridge |
| N3 | Attributes depending on part of a composite key move out (2NF) | Dependency check on composite-key tables | New entity at the partial key |
| N4 | Attributes depending on a non-key attribute move out (3NF), **only when the dependency holds with zero exceptions** | Does each `locality` always come with the same `region`? | New entity keyed by `locality`; parent keeps `locality` as FK |
| N5 | Hierarchies become one entity per level, each pointing to its parent level | Chained dependencies, e.g. `_locality → _region → _country` | `country` ← `region` ← `locality` |
| N6 | SCD2 history stays on the base entity that owns it; extracted entities are not versioned | Landing `scd_valid_from/to_timestamp`, `is_current` | Validity columns only on base entities |
| N7 | Every coded attribute becomes an extracted entity named after its domain, collecting values from every table and column in that domain, even when only one table has it | Column-name semantics + value overlap + low cardinality | One entity per domain, its attributes in 3NF |
| N8 | Raw values kept exactly; `rdm_proposed_match_key` groups obvious variants with fixed rules: trim, collapse inner whitespace, uppercase, strip accents | Always | `AUSTRALIA`, `Australia`, `AuStRaLiA` = 3 rows, 1 match key; `São Paulo` → `SAO PAULO` |
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
by case, in the spec with the reason in `design.md`; the exception rows
then go to `{entity}_quarantine` (same pattern as ACNC's and ISO's bronze
quarantine tables).

## Extracted entities

Named after the domain only, singular: `silver_normalised_neon.country`.
The schema already says which source it belongs to.

**`silver_normalised_neon.country`** — one row per distinct raw value

| Column | Example | Notes |
| --- | --- | --- |
| `country` | `AuStRaLiA` | Natural key, exactly as in Landing |
| `country_code` | `AU` | Only if the source carries it; any dependent attribute lives here |
| `rdm_proposed_match_key` | `AUSTRALIA` | Hint for rdm (N8); never used inside Silver |
| `row_count` | `3` | Occurrences across all tables and SCD2 versions |
| `ingested_timestamp` | | Max over the aggregated Landing rows |
| `transformed_timestamp` | | Per NAMING.md |

**`silver_normalised_neon.value_lineage`** — one per source, for all
extracted entities

| `entity` | `value` | `source_table` | `source_column` | `row_count` |
| --- | --- | --- | --- | --- |
| country | `AuStRaLiA` | customers | country | 2 |
| country | `AuStRaLiA` | orders | shipping_country | 1 |

Plus `ingested_timestamp` (max) and `transformed_timestamp`. Lineage is
for people, not matching: `AU` in a phone-prefix column is not `AU` in an
address, and it makes impact analysis possible.

**Order status across sources.** Sources A and B both have an order status
column, possibly in one table each. N7 still applies: each gets its own
`order_status` extracted entity (`SHIPPED`, `Shipped`, `CANCELLED` in A;
`dispatched`, `void`, `open` in B). No authoritative dataset exists; see
rdm's "curate, then match" below.

Two details fixed now:
- Values are collected from **all SCD2 versions**, not only `is_current`,
  so historical facts can still be mapped.
- A domain is decided by meaning, not column name: `billing_country` and
  `ship_to_ctry` both belong to `country`. The spec lists members
  explicitly, so it is a reviewed decision, not a runtime heuristic.

## Timestamps

- `transformed_timestamp`: stamped on every table at its own refresh,
  per NAMING.md.
- `ingested_timestamp`: base and bridge entities pass it through from
  their Landing row; extracted entities and `value_lineage` carry
  `max()` of the aggregated rows — "the newest ingest that contributed to
  this row", a freshness signal consistent with the column's meaning.
  `min()` was rejected: every `_raw` table is a materialized view whose
  `ingested_timestamp` is restamped on each run, so `min()` would look like
  "first ingested" without being that.
- **Precondition, not an optional branch**: the generic pipeline requires
  `ingested_timestamp` in the source's Landing tables and never handles it
  absent. A source without it is retrofitted at bronze in its own small
  change, just in time, before its Normalised proposal (step 0 of "Adding
  a source"). Only sources actually being normalised are retrofitted.
- First-seen / last-seen timestamps are **not** part of v0.1. Neither
  `ingested_timestamp` (restamped per MV run, absent on five sources) nor
  SCD2 validity (absent on SCD1-sourced Landing tables) gives a true
  first-seen value today, and rdm does not need them (it uses the match
  key and `value_lineage`). Add later, with a real definition, when a
  consumer needs them.

## The normalised spec

| Term | What it is | Location | Audience |
| --- | --- | --- | --- |
| **Normalised spec** | One YAML file per source describing its normalised entities; the only per-source artefact the pipeline executes | `src/layers/silver/normalised/specs/{source}.yml` | Pipeline, reviewer |
| **Normalised spec schema** | JSON Schema every normalised spec must follow; each attribute carries a one-line description | `docs/normalised-spec/schema.json` | CI, agent |
| **Normalised spec README** | Rationale, meaning of every attribute, when and how the format may be extended, "Adding a source" steps | `docs/normalised-spec/README.md` | People |

"Spec" is only used with the "normalised" qualifier, since openspec has
its own `specs/`. The schema is written in this change (not deferred to
4d) because the agent validates against it when tried on acnc. The bundle
has no `sync` block, so `docs/` is already deployed with it by default;
if 4d validates specs at run time, it can read the schema from the bundle
without extra config.

Example for acnc (column names illustrative until profiled):

```yaml
source_system: acnc
base_entities:
  charity_register:
    from: silver_landing_acnc.charity_register
    natural_key: [abn]
    history: scd2            # N6: keep validity columns
    columns: [charity_legal_name, charity_size, date_established]
    extracted:               # N10: column -> extracted entity
      address_country: country
      address_state: state
  charity_register_operating_country:  # N2: delimited list -> bridge
    from: silver_landing_acnc.charity_register
    parent: charity_register
    explode: {column: operating_countries, split: ";"}
    extracted: {value: country}
  charity_register_beneficiary:        # N2: flag column family -> bridge
    from: silver_landing_acnc.charity_register
    parent: charity_register
    unpivot: {columns_like: "beneficiary_%", keep_when: "Y"}
    extracted: {attribute: beneficiary_type}
extracted_entities:
  country:          {}
  state:            {parent: country}   # N5
  beneficiary_type: {}
ignored_columns: []           # every Landing column is used or listed here
```

An entry under `base_entities` with `parent` plus `explode` or `unpivot`
is a bridge (tagged `mdp.entity_kind = bridge`); there is no separate
block. No `rdm` block: the spec describes Silver only, and rdm finds
extracted entities by tag.

**Schema v0.1 attributes**

| Attribute | Required | Meaning |
| --- | --- | --- |
| `source_system` | yes | Matches the `silver_landing_{source}` schema suffix |
| `base_entities.{name}.from` | yes | Landing table it is built from |
| `base_entities.{name}.natural_key` | yes | Column list; becomes the first columns (N1) |
| `base_entities.{name}.history` | no | `scd2` keeps validity columns (N6); default none |
| `base_entities.{name}.columns` | yes | Attributes kept on the entity |
| `base_entities.{name}.extracted` | no | Map of column → extracted entity (N10) |
| `base_entities.{name}.parent` | no | Parent entity; with `explode`/`unpivot`, marks a bridge (N2) |
| `base_entities.{name}.explode` / `unpivot` | no | How a repeating group is flattened (N2) |
| `extracted_entities.{name}.parent` | no | Parent level in a hierarchy (N5) |
| `extracted_entities.{name}.attributes` | no | Extra dependent columns, e.g. `country_code` (N7) |
| `dependency_tolerance` | no | Per-case exception to N4's zero-exception rule; needs a reason in `design.md` |
| `ignored_columns` | yes | Landing columns deliberately left out; lets the drift check pass |

**Extending the format.** Add an attribute only when a real source needs
it, as a schema minor version bump in its own change, with the README
updated in the same PR. Removing or renaming an attribute is a major
version bump and must migrate every existing spec. Bridge support
(`parent` + `explode`/`unpivot`) is explicitly revisitable: if bridges
prove unnecessary across the first sources, they may be removed this way.

## The design-time agent

Split across three files so the instructions exist in exactly one place:

| File | Role |
| --- | --- |
| `docs/templates/silver-normalised-propose.prompt.md` | The prompt template: the single copy of the agent's instructions |
| `.claude/skills/silver-normalised-propose/SKILL.md` | Thin wrapper that loads the template, so the two cannot drift |
| `docs/templates/silver-normalised-design.md` | Skeleton for a source change's `design.md` (plain md, since the openspec version in use has no custom templates) |

What the template tells the agent to do, on Opus:
1. **Profile, pass 1**: run the standard profiling job for the source
   (below) and read its column stats and value overlaps.
2. **Find domains**: from the value overlaps between string columns across
   tables, plus name semantics (`country`, `ctry`, `state`, `status`,
   `category`, `currency`).
3. **Find dependencies, pass 2**: rerun the job with the candidate pairs
   the agent picked; it returns a zero-exception check per pair, e.g.
   ```sql
   SELECT count(*) AS violating_keys
   FROM (SELECT _locality FROM t GROUP BY _locality
         HAVING count(DISTINCT _region) > 1)
   ```
4. **Propose** the normalised spec YAML, valid against the schema, plus a
   `design.md` from the skeleton explaining every split and citing the
   profile numbers.
5. **Stop for review**: the propose PR carries the spec; nothing is
   deployed from an unreviewed spec.

Fixed inputs: `silver.md` (N1–N10), `NAMING.md`,
`docs/registers/data-sources.md`, the schema and its README.

### Standard profiling job

`src/layers/silver/normalised/profile.py`, run by
`resources/jobs/profile_silver_normalised.job.yml`
(`profile--silver_normalised--${bundle.target}`), serverless.

- **Parameters**: `source` (required, the `silver_landing_{source}` schema
  suffix); `dependency_pairs` (optional, JSON list of
  `{table, determinant, dependent}`).
- **Pass 1** (no `dependency_pairs`): for every table in
  `silver_landing_{source}`, per column: type, null %, distinct count, top
  20 values with counts, max length, and whether a common delimiter
  (`;`, `,`, `|`) appears; plus distinct-value overlap counts between
  string columns across the source's tables.
- **Pass 2** (with `dependency_pairs`): the number of violating
  determinant values per pair (the zero-exception query above).
  All-pairs checking is not done: on a wide table it is quadratic in
  column count, too heavy for Free Edition's shared serverless pool.
- **Output**: one JSON document returned as the notebook's run output
  (`dbutils.notebook.exit`), fetched by the agent with
  `databricks jobs get-run-output` and saved as `profile.json` in the
  source's openspec change folder, which is the durable copy. Nothing is
  written to a table or volume, so the job needs no new schema, volume or
  Terraform change.
- Reads only `silver_landing_{source}`; profiles all SCD2 versions, not
  only `is_current`, matching N7.
- Verified in this change by running both passes against acnc in `dev`.
  The profile's field names are the contract the prompt template and the
  design.md skeleton refer to.

## rdm: the downstream component

Context only, seeding `docs/component/rdm/README.md`; not built here. rdm
is a future Databricks app in this repo. It depends on Silver Normalised;
Silver Normalised never reads rdm.

**Consumes**: every table tagged `mdp.layer = silver_normalised` and
`mdp.entity_kind = extracted` across sources; `rdm_proposed_match_key`, so
the three Australia spellings become one decision; `value_lineage`, to
show stewards where a value came from.

| Use case | When | Example | Authoritative dataset |
| --- | --- | --- | --- |
| Match | An external standard exists | `country` → ISO 3166 | Already landed: `silver_landing_iso.*`, `silver_landing_geonames.*` |
| Curate, then match | No external standard exists | `order_status` from A and B | Created in rdm: a steward, with gen AI suggesting clusters, builds the list from the union of source entities; it is then owned in rdm and matched as in the first case |

**Writes**: `rdm.crosswalk`, owned by rdm — `source_system`, `entity`,
`value` (e.g. neon, country, `AuStRaLiA`); `authoritative_dataset`,
`authoritative_code` (iso_3166_1, AU); `match_method` (exact, rule, genai,
steward); `confidence`; `status` (proposed, approved, rejected);
`approved_by`, `approved_timestamp`. It keys on the natural key
(`source_system`, `entity`, `value`), which is why Silver Normalised needs
no surrogate keys. Only `approved` rows flow to Domain; exact and rule
matches can auto-approve, leaving gen AI only the long tail.

## Applied to current sources

First-pass hypotheses from the data-sources registry, not from profiling;
the agent confirms or discards each.

| Source | Likely extracted entities | Likely structural splits | Fit as pilot |
| --- | --- | --- | --- |
| acnc | country, state, charity_size, beneficiary_type | Operating-countries list and beneficiary/operates-in flag families → bridges (N2) | Best: exercises N2, N7, N10 and has a clear country domain |
| neon | country, order_status, product_category | Customer attributes repeated on orders, if any (N4) | Good second: classic OLTP, multi-table country domain |
| airroi | country, region, locality, district | Market hierarchy (N5) | Good for hierarchies |
| ungm | segment, family, class | UNSPSC 4-level hierarchy (N5) | Mostly structural, little rdm value |
| nsw_spatial | suburb, lga, postcode | Property → lot/plan splits (N3/N4) | Later |
| clickstream | country, device, browser, event_type | Event already narrow | Later |
| iso, geonames | none | Already authoritative | Skip: rdm's authoritative targets, not inputs |

## SDLC and artefacts

A **framework change**, done once (4c design time: rules, spec format,
agent, profiling; 4d run time: pipeline, verification, CI), builds the
machinery; each **source change** then adds little more than one spec
file. Both follow CONTRIBUTING's propose PR → implement PR flow.

**Per-source steps** (live in `docs/normalised-spec/README.md`, "Adding a
source"):
0. **Precondition**: if the source's Landing tables lack
   `ingested_timestamp`, retrofit bronze in its own change first.
1. **Branch** `feature/silver-normalised-{source}`.
2. **Profile** on dev with the standard profiling job (both passes); the
   JSON run output is saved into the openspec change folder as
   `profile.json`.
3. **Propose**: run the agent skill on Opus; it writes the normalised spec
   and the openspec change (`proposal.md`, `design.md` from the skeleton,
   `tasks.md`).
4. **PR 1**: the real design review — entities, domains, splits.
5. **Implement** on Sonnet: bundle resources pointing the generic pipeline
   at the spec, the orchestrating job, verification, the data-sources.md
   entry; `silver_normalised_{source}` schema and grants in
   `demo-databricks-iac` first (cross-repo dependency).
6. **Validate, deploy to dev, verify**: base parity, bridge element count,
   extracted value completeness, FK integrity, no Landing drift.
7. **PR 2**: merge, then archive.
8. **rdm picks up** the newly tagged extracted entities, in its own process.

When Landing gains or changes columns, the drift check fails and the
source goes back to step 2.

**Artefacts** (paths follow the repo's existing layout)

| Artefact | Path | Created by |
| --- | --- | --- |
| Layer definition, N1–N10, agent-instructions subsection | `docs/medallion/silver.md` | 4c |
| Naming rules for this layer | `NAMING.md` | 4c |
| Normalised spec schema | `docs/normalised-spec/schema.json` | 4c |
| Normalised spec README | `docs/normalised-spec/README.md` | 4c |
| Prompt template | `docs/templates/silver-normalised-propose.prompt.md` | 4c |
| design.md skeleton | `docs/templates/silver-normalised-design.md` | 4c |
| Agent skill (thin wrapper) + skills README entry | `.claude/skills/silver-normalised-propose/SKILL.md`, `docs/skills/README.md` | 4c |
| rdm component doc (seed) | `docs/component/rdm/README.md` | 4c |
| Decision register entries | `docs/decision-register.md` | 4c |
| Profiling notebook + job | `src/layers/silver/normalised/profile.py`, `resources/jobs/profile_silver_normalised.job.yml` | 4c |
| Generic pipeline | `src/layers/silver/normalised/pipeline.py` | 4d |
| Generic verification incl. drift check | `verification/verify_silver_normalised.py`, `resources/jobs/verify_silver_normalised.job.yml` | 4d |
| CI step validating every normalised spec against the schema | `.github/workflows/pr.yml` | 4d |
| Profile evidence | `openspec/changes/<change>/profile.json` (the job's run output) | Source, step 2 |
| Normalised spec | `src/layers/silver/normalised/specs/{source}.yml` | Source, step 3 |
| Bundle resources | `resources/pipelines/silver_normalised_{source}.pipeline.yml`, `resources/jobs/silver_{source}.job.yml` | Source, step 5 |
| Schema and grants | `silver_normalised_{source}` in `demo-databricks-iac` | Source, before step 5 |
| Registry entry | `docs/registers/data-sources.md`, "Consumed by Silver Normalised" | Source, step 5 |

**Rollout**
1. `phase4c-silver-normalised-docs` (Opus): this change — every 4c row
   above, design time.
2. `phase4d-silver-normalised-framework` (Opus): every 4d row above, run
   time.
3. `phase4e-silver-normalised-acnc` (Opus propose, Sonnet implement),
   preceded by acnc's `ingested_timestamp` retrofit.
4. One source at a time after that; Sonnet once the pattern holds.
5. rdm as its own later changes, from `docs/component/rdm/README.md`.

## Decisions

Each becomes a `docs/decision-register.md` entry.

- **Gen AI at design time only** — alternatives: rules in md only (bespoke
  code per source), `ai_query` in the pipeline (non-deterministic).
- **Terminology**: normalised / base / bridge / extracted entity;
  "reference" avoided because it reads as authoritative.
- **Naming**: base entities keep the Landing table name; extracted
  entities use the singular domain name only (the schema carries the
  source); bridges are `{parent}_{attribute}`. Alternative: renaming base
  entities to a cleaner singular (`charity`) — rejected, it breaks the
  one-to-one traceability back to Landing.
- **No generated surrogate keys** here; deferred beyond this layer. The
  rdm crosswalk keys on the natural key.
- **Single-table coded columns** become extracted entities too; they feed
  rdm's curate use case.
- **Match hint** `rdm_proposed_match_key` stays in Silver, fixed rules only.
- **Lineage**: one `value_lineage` table per source.
- **Dependency tolerance**: zero exceptions by default; per-case
  tolerances only via the spec with a reason, exceptions to
  `{entity}_quarantine` (widening NAMING.md's bronze-only `_quarantine`).
- **Bridges as their own entity kind**, with an element-count check
  instead of row parity; revisitable if bridges prove unnecessary.
- **`ingested_timestamp`**: `max()` on aggregated entities; required in
  Landing as a precondition, retrofitted per source just in time.
  Alternatives: optional/absent handling in the pipeline (more code
  paths), retrofitting all five sources now (touches sources that may
  never be normalised).
- **No first/last-seen columns in v0.1** (no reliable source today).
- **Dependency direction**: rdm consumes Silver Normalised, never the
  reverse; the spec has no `rdm` block.
- **Tags**: plain Unity Catalog tags `mdp.layer`, `mdp.source_system`,
  `mdp.entity_kind = base | bridge | extracted`. Governed tags (tag
  policies enforcing allowed values) deferred to the planning roadmap
  backlog, to discuss once Silver Normalised is finalised.
- **Profiling job in 4c, not 4d**: the framework is split by design time
  (4c: what the agent needs to propose) vs run time (4d: what executes a
  spec), not docs vs code. Alternative: ad-hoc SQL until 4d — rejected,
  it gives the acnc trial evidence in a different shape from every later
  source.
- **Profile returned as run output, not written to a volume**: avoids a
  Terraform-owned volume and a cross-repo dependency; the durable copy is
  `profile.json` in the openspec change. Alternative: JSON files on a UC
  volume, as the planning draft suggested.
- **Two-pass profiling**: dependency checks only for agent-chosen pairs.
  Alternative: all column pairs — quadratic, too heavy for Free Edition.
- **Drift check** runs in the verification job, not CI; CI only validates
  specs against the schema.
- **Change IDs** renumbered from the planning session's `phase4b1`/`4b2`
  to `phase4c`/`4d`/`4e`, since `phase4b` is already Silver Landing for
  ISO/GeoNames.

## Risks / Trade-offs

- [Rules only enforced by review until 4d] → acceptable: nothing is
  deployed from a spec before 4d exists; 4d adds schema validation in CI
  and the drift check in verification.
- [Profile JSON exceeds the notebook run-output size limit on a wide or
  high-cardinality source] → confirm the limit when building the job;
  top-N values are already capped at 20. If a real source exceeds it, the
  fallback is a volume, as its own change with the Terraform dependency.
- [Profiling competes for Free Edition's shared serverless pool] → run it
  alone, per this repo's one-run-at-a-time rule; pass 2 checks only chosen
  pairs.
- [Zero-exception rule keeps some attributes denormalised] → intended:
  spelling variants are rdm's job; a tolerance can be declared per case.
- [Precondition delays sources lacking `ingested_timestamp`] → one small
  retrofit change per source; neon may need the column stamped one layer
  later, since Lakeflow Connect writes its `_raw` tables.
- [Schema v0.1 may not fit the first real source] → minor version bumps
  are cheap and expected; the pilot (acnc) is chosen to exercise most rules.

## Migration Plan

One new job, deployed to `dev` by the implementation PR and to `tst`/`prd`
by CI/CD on merge, per this repo's operational notes. It reads only and
writes no data, so rollback is reverting the PR and letting the next
deploy remove the job.

## Open Questions

- How plain Unity Catalog tags are applied to pipeline-managed tables (in
  the dataset definition vs. a post-refresh step) — decided in 4d; the tag
  names above do not change.
- Where neon's `ingested_timestamp` is stamped, given Lakeflow Connect owns
  its `_raw` tables — decided in neon's retrofit change.
