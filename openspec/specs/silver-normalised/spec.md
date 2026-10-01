# silver-normalised Specification

## Purpose
Silver Normalised restructures one source's Silver Landing tables at a
time into third normal form and extracts every coded attribute into its
own entity, without changing any value, so downstream matching (rdm) and
later Silver sub-layers work from a clean, source-aligned structure.

## Requirements

### Requirement: Source-aligned schema and inputs
Each source SHALL have its Silver Normalised tables in a schema named
`silver_normalised_{source_system}`. Those tables SHALL read only from the
same source's `silver_landing_{source_system}` tables: no cross-source
joins, and no reads from rdm or any other downstream component.

#### Scenario: Table reads another source
- **WHEN** a proposed Silver Normalised table for source A reads from any
  schema other than `silver_landing_A`
- **THEN** the proposal is rejected in review and the table is not built

### Requirement: Structural change only
Silver Normalised SHALL NOT correct, map, trim or otherwise change any
value taken from Silver Landing. Values SHALL appear exactly as they are
in Landing; the only derived value columns permitted are the ones these
requirements define (`rdm_proposed_match_key`, `row_count`, and the
platform timestamp columns).

#### Scenario: Spelling variants in Landing
- **WHEN** Landing contains `AUSTRALIA`, `Australia` and `AuStRaLiA` in a
  country column
- **THEN** the `country` extracted entity holds three rows, one per raw
  value, each unchanged

### Requirement: Deterministic output without run-time LLM calls
Silver Normalised SHALL produce the same rows for the same Landing input
on every refresh, and SHALL NOT call an LLM (e.g. `ai_query`) at run time.

#### Scenario: Refresh with unchanged Landing
- **WHEN** a Silver Normalised pipeline is refreshed twice with no change
  to its Landing input
- **THEN** both refreshes produce identical rows, apart from
  `transformed_timestamp`

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

### Requirement: Materialized output
Silver Normalised tables SHALL be materialized views, since every input is
an upsert-maintained Silver Landing materialized view, not an append-only
source.

#### Scenario: Landing row updated in place
- **WHEN** a Landing row is updated in place by its refresh
- **THEN** the next Silver Normalised refresh reflects the update without
  a streaming-source failure

### Requirement: Natural keys, no generated surrogate key (N1)
Every entity SHALL be identified by its natural key, placed as its first
column(s), with each natural-key column's comment stating that it is part
of the natural key. Silver Normalised SHALL NOT generate a surrogate key;
if the Landing table already carries one from Bronze Publish, a base
entity passes it through as its first column, ahead of the natural key.

#### Scenario: Base entity column order
- **WHEN** a base entity is built from a Landing table with natural key
  `abn` and no surrogate key
- **THEN** `abn` is the entity's first column, its comment states it is
  the natural key, and no surrogate key column exists

### Requirement: Base entities keep Landing name and row-count parity
A base entity SHALL keep its Landing table's name and grain. Its row count
plus the row count of its `{entity}_quarantine` table (if one exists)
SHALL equal the Landing table's row count.

#### Scenario: Parity check
- **WHEN** `silver_landing_acnc.charity_register` has 500 rows and no
  quarantine table exists
- **THEN** `silver_normalised_acnc.charity_register` has 500 rows

### Requirement: Repeating groups become bridge entities (N2)
A delimited list column, or a family of numbered or flag columns, SHALL be
flattened into a bridge entity named `{parent}_{attribute}`, keyed by the
parent's natural key plus the element. A bridge's row count SHALL equal
the number of non-null list elements (or flags set to their "true" value)
in the Landing table. A flag family SHALL be selected by a name pattern or,
when its columns share none, by an explicit column list.

#### Scenario: Delimited list
- **WHEN** a charity's Landing row has `operating_countries = 'AU;NZ;FJ'`
- **THEN** the bridge `charity_register_operating_country` holds three rows
  for that charity, one per country value

#### Scenario: Flag family without a shared prefix
- **WHEN** a spec lists `Adults`, `Children` and `Youth` as one family and
  a charity has `Y` in `Adults` and `Youth`
- **THEN** the bridge holds two rows for that charity, `Adults` and `Youth`

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

### Requirement: Hierarchies, one entity per level (N5)
A chain of zero-exception dependencies (e.g. locality → region → country)
SHALL become one extracted entity per level, each carrying its parent
level's key as a foreign key.

#### Scenario: Three-level hierarchy
- **WHEN** locality → region → country holds with zero exceptions
- **THEN** `locality` references `region` and `region` references
  `country`

### Requirement: History only on base entities (N6)
SCD2 validity columns (`scd_valid_from_timestamp`,
`scd_valid_to_timestamp`, `is_current`) SHALL be kept only on base
entities whose Landing table has them. Bridge entities inherit their
parent row's validity; extracted entities SHALL NOT be versioned.

#### Scenario: SCD2 Landing source
- **WHEN** a base entity's Landing table carries SCD2 validity columns
- **THEN** the base entity keeps them and the extracted entities built
  from it carry none

### Requirement: One extracted entity per domain (N7)
Every coded attribute SHALL become an extracted entity named after its
domain in singular form (`country`, `order_status`), collecting the
distinct values of every column the source's normalised spec assigns to
that domain, across all tables and across all SCD2 versions (not only
current ones), even when only one column has it. Every non-null Landing
value in a member column SHALL have a row (value completeness).

#### Scenario: Two columns, one domain
- **WHEN** the spec assigns `customers.country` and
  `orders.shipping_country` to domain `country`
- **THEN** `silver_normalised_{source}.country` contains every distinct
  non-null value from both columns, including values seen only in
  historical SCD2 versions

### Requirement: Match-key hint (N8)
Every extracted entity SHALL carry an `rdm_proposed_match_key` column
computed by fixed rules only: trim, collapse inner whitespace, uppercase,
strip accents. It SHALL NOT be used by any logic inside Silver.

#### Scenario: Variants share a match key
- **WHEN** an extracted entity holds `AUSTRALIA`, `Australia` and
  `AuStRaLiA`
- **THEN** all three rows have `rdm_proposed_match_key = 'AUSTRALIA'`, and
  `São Paulo` gets `SAO PAULO`

### Requirement: Value lineage (N9)
Each source SHALL have one `value_lineage` table recording, for every
extracted value, the entity, the value, and each source table and column
where it was seen, with a row count per location.

#### Scenario: Value seen in two columns
- **WHEN** `AuStRaLiA` appears twice in `customers.country` and once in
  `orders.shipping_country`
- **THEN** `value_lineage` has two rows for it, with row counts 2 and 1

### Requirement: Foreign keys stay, dependent attributes move (N10)
A base entity SHALL keep each coded column as a foreign key to its
extracted entity; attributes that depend on that code SHALL live only in
the extracted entity.

#### Scenario: Country code and name
- **WHEN** Landing carries both `country` and `country_name`
- **THEN** the base entity keeps `country` and only the `country`
  extracted entity carries `country_name`

### Requirement: Platform timestamp columns
Every Silver Normalised table SHALL stamp `transformed_timestamp` at its
own refresh. A source's Landing tables SHALL carry `ingested_timestamp`
before that source is normalised. Base and bridge entities SHALL pass
`ingested_timestamp` through unchanged from their Landing row; extracted
entities and `value_lineage` SHALL carry the maximum `ingested_timestamp`
of the Landing rows they aggregate.

#### Scenario: Extracted value from rows of different ages
- **WHEN** a country value is aggregated from Landing rows ingested at T1
  and T2, with T2 later than T1
- **THEN** its extracted-entity row has `ingested_timestamp = T2`

### Requirement: Every source driven by a reviewed normalised spec
Each normalised source SHALL be described by exactly one normalised spec
that validates against the normalised spec schema and was reviewed in that
source's propose PR. Every column of every Landing table the spec reads
SHALL appear in the spec, either used or listed in `ignored_columns`.

#### Scenario: Landing gains a column
- **WHEN** a Landing table gains a column that the source's normalised spec
  neither uses nor lists in `ignored_columns`
- **THEN** the source's drift check fails and the source returns to
  profiling and proposal

### Requirement: Standard profiling evidence
A standard profiling job SHALL profile one source's Silver Landing tables,
across all SCD2 versions, and return the result as a single JSON document
without writing to any table or volume. Without dependency pairs it SHALL
return, per column, type, null %, distinct count, top 20 values with
counts, max length and delimiter presence, plus distinct-value overlap
counts between string columns across the source's tables. Given a list of
dependency pairs, it SHALL return the number of violating determinant
values per pair. Dependency evidence SHALL come from the source's full
dataset: when `dev` is row-limited, either the limit is lifted for `dev`
or the dependency checks run read-only against `prd`.

#### Scenario: First profiling pass
- **WHEN** the profiling job runs for `acnc` with no dependency pairs
- **THEN** it returns JSON with column statistics for every column of every
  `silver_landing_acnc` table and the cross-table value overlaps, and no
  table or volume is written

#### Scenario: Dependency pass
- **WHEN** the profiling job runs with a dependency pair whose determinant
  maps to more than one dependent value for 3 determinant values
- **THEN** it reports 3 violating values for that pair

#### Scenario: Row-limited source
- **WHEN** a source's `dev` holds a 500-row sample of a 66k-row dataset
- **THEN** its proposed splits rest on dependency checks over the full
  dataset, not the sample

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
`transformed_timestamp`. It SHALL be built from the same non-quarantined
Landing rows as its base entities and from its bridge entities, never
choosing one of several recorded values. A blank (null) parent SHALL NOT
count as a value: a value recorded with exactly one non-null parent and
some null parents SHALL get one row with that parent, and a value recorded
only with null parents SHALL get one row with a null parent.

#### Scenario: Dependency broken by new data
- **WHEN** a later refresh brings locality `Prado` with a second region
- **THEN** the `locality` entity holds two `Prado` rows and verification
  fails on extracted-key uniqueness

#### Scenario: Blank parent alongside a recorded one
- **WHEN** postcode `2000` appears with state `NSW` on two rows and with a
  null state on one row
- **THEN** the `postcode` entity holds one `2000` row with state `NSW` and
  a `row_count` of 3

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
`ingested_timestamp` SHALL be checked non-null only on current rows of
SCD2 base entities (and on every row of other base entities), since SCD2
versions closed before a source's `ingested_timestamp` retrofit keep it
null.

#### Scenario: Clean source
- **WHEN** verification runs for a source whose tables match its spec and
  Landing
- **THEN** the job succeeds and reports the number of tables checked

#### Scenario: Version closed before the retrofit
- **WHEN** a base entity has a closed SCD2 version with a null
  `ingested_timestamp` and every current row has one
- **THEN** the timestamp check passes

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
