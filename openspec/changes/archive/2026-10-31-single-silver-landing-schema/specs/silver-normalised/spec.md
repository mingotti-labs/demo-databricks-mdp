## MODIFIED Requirements

### Requirement: Source-aligned schema and inputs
Each source SHALL have its Silver Normalised tables in a schema named
`silver_normalised_{source_system}`. Those tables SHALL read only from the
same source's Silver Landing tables, `silver_landing.{source_system}__*`: no cross-source
joins, and no reads from rdm or any other downstream component.

#### Scenario: Table reads another source
- **WHEN** a proposed Silver Normalised table for source A reads from any
  table other than `silver_landing.A__*`
- **THEN** the proposal is rejected in review and the table is not built

### Requirement: Base entities keep Landing name and row-count parity
A base entity SHALL keep its Landing table's entity name (without the
`{source_system}__` prefix) and grain. Its row count
plus the row count of its `{entity}_quarantine` table (if one exists)
SHALL equal the Landing table's row count.

#### Scenario: Parity check
- **WHEN** `silver_landing.acnc__charity_register` has 500 rows and no
  quarantine table exists
- **THEN** `silver_normalised_acnc.charity_register` has 500 rows

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
  `silver_landing.acnc__*` table and the cross-table value overlaps, and no
  table or volume is written

#### Scenario: Dependency pass
- **WHEN** the profiling job runs with a dependency pair whose determinant
  maps to more than one dependent value for 3 determinant values
- **THEN** it reports 3 violating values for that pair

#### Scenario: Row-limited source
- **WHEN** a source's `dev` holds a 500-row sample of a 66k-row dataset
- **THEN** its proposed splits rest on dependency checks over the full
  dataset, not the sample

### Requirement: Spec cross-references checked before building
The pipeline SHALL load and check the normalised spec before defining any
table, and SHALL fail without building anything when the spec breaks a
cross-reference rule the schema cannot express: a `from` outside
`silver_landing.{source_system}__*`, a duplicate or reserved entity name, a
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
