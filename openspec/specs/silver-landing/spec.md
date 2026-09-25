# silver-landing Specification

## Purpose
Silver Landing exposes each Bronze Publish source's data into Silver as a
source-aligned, standardized foundational data product, with no
cross-source joins or business logic, so later Silver sub-layers have a
stable and consistent starting point.

## Requirements

### Requirement: Source-aligned table per Bronze Publish entity
For every entity Bronze Publish exposes at least one SCD object for, there
SHALL be exactly one corresponding Silver Landing table, in a schema named
`silver_landing_{source_system}`, using the entity's datasource name (not
the Bronze Publish object's SCD-suffixed name) as the table name.

#### Scenario: Entity published to Bronze Publish
- **WHEN** a Bronze Publish schema contains at least one SCD object for an
  entity
- **THEN** `silver_landing_{source_system}` contains a table named after
  that entity

### Requirement: SCD variant selection precedence
When a Bronze Publish entity has more than one SCD object available, Silver
Landing SHALL select the source object by precedence: SCD2 first, then
SCD1, then SCD0 (raw). Only one variant lands per entity.

#### Scenario: Both SCD2 and SCD1 exist
- **WHEN** a Bronze Publish entity has both a SCD2 and a SCD1 object
- **THEN** the Silver Landing table is sourced from the SCD2 object

#### Scenario: Only SCD1 exists
- **WHEN** a Bronze Publish entity has a SCD1 object and no SCD2 object
- **THEN** the Silver Landing table is sourced from the SCD1 object

### Requirement: Materialized output, not a streaming read
Silver Landing tables reading from a Bronze Publish SCD1/SCD2 object SHALL
be materialized (e.g. a materialized view), not implemented as a streaming
table reading directly from that object, because Bronze Publish SCD1/SCD2
objects are upsert-maintained and not append-only.

#### Scenario: Source is an upsert-maintained SCD object
- **WHEN** the selected Bronze Publish source object is an Auto CDC
  SCD1/SCD2 object
- **THEN** the Silver Landing table is defined as a materialized view, not
  a streaming table

### Requirement: Provenance metadata on every row
Every Silver Landing table SHALL include `source_name`, `transformed_timestamp`,
and `source_file_name` columns. `transformed_timestamp` SHALL be stamped
with the current timestamp at Silver Landing's own refresh — Silver Landing
SHALL NOT stamp or otherwise modify `ingested_timestamp`; if the selected
Bronze Publish source object already carries one, it is propagated
unchanged, and if it doesn't, the column is simply absent. `source_file_name`
is populated only when the underlying Bronze Publish object carries a
source file name column to propagate; otherwise it is null. As of this
change, no Bronze Publish object carries one (including clickstream's,
confirmed by inspecting its Auto Loader ingestion), so the column is null
on all 10 tables today — populated automatically once/if a source's bronze
layer starts capturing it.

#### Scenario: Row lands in Silver Landing
- **WHEN** a row is materialized into a Silver Landing table
- **THEN** the row includes non-null `source_name` and `transformed_timestamp`
  values, and a `source_file_name` value that is non-null only if the
  selected Bronze Publish source object carries one to propagate

#### Scenario: Bronze Publish source already has an ingested_timestamp
- **WHEN** the selected Bronze Publish source object carries an
  `ingested_timestamp` column
- **THEN** the Silver Landing table propagates that value unchanged, and
  does not overwrite it with a new value at Silver Landing's own refresh

### Requirement: Row-count parity as the first data quality gate
A Silver Landing table's row count SHALL match the row count of its
selected Bronze Publish source object as of the same refresh. A mismatch
SHALL be surfaced as a data quality failure, not silently ignored.

#### Scenario: Refresh completes with matching counts
- **WHEN** a Silver Landing table finishes refreshing
- **THEN** its row count equals the selected Bronze Publish source object's
  row count at that refresh

#### Scenario: Refresh completes with mismatched counts
- **WHEN** a Silver Landing table's row count does not match its Bronze
  Publish source object's row count
- **THEN** the mismatch is surfaced as a data quality failure on that
  refresh

### Requirement: No generated surrogate key
Silver Landing SHALL NOT generate a surrogate key. If the Bronze Publish
source object already provides one, it remains the first column; otherwise
the entity's natural key column(s) are the first column(s), in the same
order as they exist in the Bronze Publish source object.

#### Scenario: Bronze Publish source has no surrogate key
- **WHEN** the selected Bronze Publish source object provides no surrogate
  key column
- **THEN** the Silver Landing table's first column(s) are the entity's
  natural key column(s), and no surrogate key column is added

### Requirement: SCD2 current-version indicator
A Silver Landing table sourced from an SCD2 Bronze Publish object SHALL
expose an `is_current` column indicating whether a row is the entity's
currently active version.

#### Scenario: Table sourced from an SCD2 object
- **WHEN** a Silver Landing table is sourced from an SCD2 Bronze Publish
  object
- **THEN** each row has an `is_current` boolean value derived from that
  version's validity end column

### Requirement: No cross-source joins or business logic
A Silver Landing table SHALL read from exactly one Bronze Publish source
object and SHALL NOT join data from another source system or apply
business-specific mappings or derived business metrics.

#### Scenario: Defining a Silver Landing table
- **WHEN** a Silver Landing table is defined
- **THEN** its query reads from exactly one Bronze Publish source object
  and contains no joins to other source systems' Bronze Publish objects
