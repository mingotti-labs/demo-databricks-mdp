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

### Requirement: A per-load column stays out of the snapshot
In a bronze full pattern (a `_raw` table reloaded in full), a column whose value
changes on every load SHALL NOT be part of the snapshot applied to Bronze
Publish. `ingested_timestamp` is such a column; it SHALL be used only as the
snapshot's version.

#### Scenario: Unchanged load
- **WHEN** the bronze pipeline reloads `_raw` and no business column changed
- **THEN** the SCD2 table gets no write

### Requirement: An SCD2 version keeps its fetch time
On a Bronze Publish SCD2 table, `__START_AT` SHALL be the fetch time of the load
that created the version, to the millisecond, and `__END_AT` the fetch time of
the load that closed it. Neither SHALL change afterwards.

#### Scenario: One row changed
- **WHEN** a load changes one row's business columns
- **THEN** its old version gets `__END_AT` = that load's fetch time, a new version
  gets `__START_AT` = that load's fetch time, and no other row is written

### Requirement: Silver Landing settles the platform timestamps
Silver Landing SHALL read only the rows changed in its Bronze Publish SCD2 table
since its last run, SHALL hold the same rows as a full read of that table, SHALL
stamp `transformed_timestamp` on the rows it receives, and SHALL set
`ingested_timestamp` to the version's `__START_AT`. Every Landing row SHALL have
both columns populated.

#### Scenario: One bronze version closed and one inserted
- **WHEN** Bronze Publish closes one version and inserts one
- **THEN** Landing changes exactly those two rows, only they get a new
  `transformed_timestamp`, and Landing equals a full read of the SCD2 table

### Requirement: No run-time stamping on full snapshots
`current_timestamp()` SHALL NOT be applied to a full snapshot that feeds a
change-detecting step or a silver table, except as `ingested_timestamp` on a
`_raw` table.

#### Scenario: Guard test
- **WHEN** the test suite runs
- **THEN** it fails if `current_timestamp()` appears outside `_raw` files, the
  Silver Landing stream and the stamping helpers
