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
Catalog tags `mdp.layer = silver_normalised`,
`mdp.source_system = {source_system}` and
`mdp.entity_kind = base | bridge | extracted`.

#### Scenario: Extracted entity discoverable by tag
- **WHEN** a downstream consumer lists tables tagged
  `mdp.layer = silver_normalised` and `mdp.entity_kind = extracted`
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
in the Landing table.

#### Scenario: Delimited list
- **WHEN** a charity's Landing row has `operating_countries = 'AU;NZ;FJ'`
- **THEN** the bridge `charity_register_operating_country` holds three rows
  for that charity, one per country value

### Requirement: Dependency splits need zero exceptions (N3, N4)
An attribute SHALL be moved out of an entity because it depends on part of
a composite key (N3) or on a non-key attribute (N4) only when the
dependency holds with zero exceptions in Landing. A per-case tolerance is
allowed only when declared in the source's normalised spec with a reason
in that change's `design.md`; the exception rows then SHALL go to
`{entity}_quarantine`, never be silently dropped.

#### Scenario: Dependency with a spelling variant
- **WHEN** locality `Urubici` appears with region `Santa Catarina` on
  9,997 rows and `Santa Catrina` on 3 rows, and no tolerance is declared
- **THEN** `locality` is not split out and `region` stays on the base
  entity

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
values per pair.

#### Scenario: First profiling pass
- **WHEN** the profiling job runs for `acnc` with no dependency pairs
- **THEN** it returns JSON with column statistics for every column of every
  `silver_landing_acnc` table and the cross-table value overlaps, and no
  table or volume is written

#### Scenario: Dependency pass
- **WHEN** the profiling job runs with a dependency pair whose determinant
  maps to more than one dependent value for 3 determinant values
- **THEN** it reports 3 violating values for that pair
