## ADDED Requirements

### Requirement: transformed_timestamp marks only rows a step changed
`transformed_timestamp` SHALL be written only on rows that the table's own step
inserts, modifies or closes in that run. A row the step does not change SHALL
keep its previous value.

#### Scenario: Run with no source change
- **WHEN** a step runs and its input has not changed since the last run
- **THEN** no row of its table gets a new `transformed_timestamp`

#### Scenario: One row changed
- **WHEN** one source row changed since the last run
- **THEN** only the rows derived from it get a new `transformed_timestamp`

### Requirement: An SCD2 version keeps its ingestion time
On an SCD2 table, `ingested_timestamp` SHALL be the fetch time of the data that
created that version, and SHALL NOT change afterwards.

#### Scenario: Unchanged row across runs
- **WHEN** the bronze pipeline runs again and a row's business columns are unchanged
- **THEN** its current SCD2 version is not rewritten and keeps its `ingested_timestamp`

### Requirement: No run-time stamping on full snapshots
`current_timestamp()` SHALL NOT be applied to a full snapshot that feeds a
change-detecting step or a silver table, except as `ingested_timestamp` on a
`_raw` table.

#### Scenario: Guard test
- **WHEN** the test suite runs
- **THEN** it fails if `current_timestamp()` appears outside `_raw` files and the stamping helpers
