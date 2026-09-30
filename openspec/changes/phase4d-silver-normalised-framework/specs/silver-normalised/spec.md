## ADDED Requirements

### Requirement: One generic pipeline executes every normalised spec
Every normalised source SHALL be built by the same pipeline source file,
`src/layers/silver/normalised/pipeline.py`, instanced as one pipeline
resource per source named `silver--normalised--{source}--${bundle.target}`
that writes to `silver_normalised_{source}` and receives the source's
normalised spec path through its configuration. No per-source
transformation code SHALL exist.

#### Scenario: Adding a second source
- **WHEN** a second source is normalised
- **THEN** its change adds a normalised spec and bundle resources only,
  and `pipeline.py` is unchanged

### Requirement: Spec cross-references checked before building
The pipeline SHALL load and check the normalised spec before defining any
table, and SHALL fail without building anything when the spec breaks a
cross-reference rule the schema cannot express: a `from` outside
`silver_landing_{source_system}`, a duplicate or reserved entity name, a
bridge whose parent is not a base entity or whose `from` differs from its
parent's, an extracted target that is not declared, a declared extracted
entity with no member column, a missing or cyclic `parent`, a parent or
attribute that cannot be resolved from exactly one column of the same base
entity, a tolerance on columns its entity does not use, or a column both
used and ignored.

#### Scenario: Undeclared extracted entity
- **WHEN** a base entity maps `address_state` to `state` and
  `extracted_entities` has no `state`
- **THEN** the pipeline update fails before any table is refreshed, naming
  the missing entity

### Requirement: Platform columns handled by the framework
The pipeline SHALL carry `scd_valid_from_timestamp`,
`scd_valid_to_timestamp`, `is_current`, `source_name`, `source_file_name`,
`ingested_timestamp` and `transformed_timestamp` itself; a normalised spec
SHALL NOT list them. Base entities SHALL keep the validity columns only
when the spec sets `history: scd2`, and the pipeline SHALL fail if a
Landing table has validity columns but its base entity does not set it.

#### Scenario: SCD2 Landing table without history
- **WHEN** a Landing table has `scd_valid_from_timestamp` and its base
  entity omits `history`
- **THEN** the pipeline update fails with a message naming the entity

### Requirement: Extracted entity columns
Each extracted entity SHALL have, in order: the value column named after
the entity; the parent entity's value column when it has a `parent`; its
`attributes`; `rdm_proposed_match_key`; `row_count`; `ingested_timestamp`;
`transformed_timestamp`. It SHALL be built from the source's base and
bridge entities, grouping by value, parent and attributes, never choosing
one of several values.

#### Scenario: Dependency broken by new data
- **WHEN** a later refresh brings locality `Prado` with a second region
- **THEN** the `locality` entity holds two `Prado` rows and verification
  fails on extracted-key uniqueness

### Requirement: Tags applied after every refresh
After each Silver Normalised pipeline refresh, a tag step SHALL set
`mdp_layer`, `mdp_source_system` and, for base, bridge and extracted
entities, `mdp_entity_kind` on every table the source's spec produces,
using `ALTER MATERIALIZED VIEW … SET TAGS`.

#### Scenario: Orchestrated run
- **WHEN** `silver--{source}--${bundle.target}` completes
- **THEN** every entity table in `silver_normalised_{source}` carries all
  three `mdp_*` tags with the values its spec implies

### Requirement: Per-source orchestration
Each normalised source SHALL have a job `silver--{source}--${bundle.target}`
with tasks `landing` (the source's Silver Landing pipeline), `normalised`
(depends on `landing`) and `tag` (depends on `normalised`), so Silver
Normalised never reads a partial Landing refresh.

#### Scenario: Landing refresh fails
- **WHEN** the `landing` task fails
- **THEN** neither `normalised` nor `tag` runs

### Requirement: Generic verification
A verification job, `verify--silver--normalised--${bundle.target}`, SHALL
check one source at a time against its spec and fail listing every broken
check: drift (every Landing column used, ignored or a platform column,
and every used column present), base parity with quarantine, natural-key
uniqueness, bridge element counts, extracted value completeness,
extracted-key uniqueness, foreign-key integrity, `value_lineage` totals,
non-null match keys and timestamps, tags, and tolerance limits.

#### Scenario: Clean source
- **WHEN** verification runs for a source whose tables match its spec and
  Landing
- **THEN** the job succeeds and reports the number of tables checked

### Requirement: Specs validated in CI
Every pull request touching the bundle, a normalised spec, the normalised
spec schema or the tests SHALL validate every
`src/layers/silver/normalised/specs/*.yml` against
`docs/normalised-spec/schema.json` and run the unit tests, without
Databricks credentials.

#### Scenario: Invalid spec in a PR
- **WHEN** a PR adds a spec whose bridge declares both `explode` and
  `unpivot`
- **THEN** the PR's spec validation job fails

## MODIFIED Requirements

### Requirement: Entity kinds and Unity Catalog tags
Every Silver Normalised table SHALL be exactly one of three entity kinds —
base (restructured from one Landing table at that table's grain), bridge
(one row per element of a repeating group), or extracted (one row per
distinct value of a domain) — or the per-source `value_lineage` or a
`{entity}_quarantine` table. Every entity table SHALL carry the Unity
Catalog tags `mdp_layer = silver_normalised`,
`mdp_source_system = {source_system}` and
`mdp_entity_kind = base | bridge | extracted`. Tag keys SHALL NOT contain
`.`, which Unity Catalog rejects as a reserved character.

#### Scenario: Extracted entity discoverable by tag
- **WHEN** a downstream consumer lists tables tagged
  `mdp_layer = silver_normalised` and `mdp_entity_kind = extracted`
- **THEN** every extracted entity of every normalised source is returned

### Requirement: Dependency splits need zero exceptions (N3, N4)
An attribute SHALL be moved out of an entity because it depends on part of
a composite key (N3) or on a non-key attribute (N4) only when the
dependency holds with zero exceptions in Landing. A per-case tolerance is
allowed only when declared in the source's normalised spec with a reason
in that change's `design.md`; the exception rows then SHALL go to
`{entity}_quarantine`, never be silently dropped. A split SHALL NOT remove
a column of the Landing natural key from a base entity; dependencies among
key columns are captured by the extracted-entity hierarchy (N5).

#### Scenario: Dependency with a spelling variant
- **WHEN** locality `Urubici` appears with region `Santa Catarina` on
  9,997 rows and `Santa Catrina` on 3 rows, and no tolerance is declared
- **THEN** `locality` is not split out and `region` stays on the base
  entity

#### Scenario: Dependency among key columns
- **WHEN** a base entity's natural key is `_country, _region, _locality`
  and `_locality → _region → _country` holds with zero exceptions
- **THEN** all three columns stay in the base entity's natural key, and
  the hierarchy is expressed as `locality` → `region` → `country`
  extracted entities
