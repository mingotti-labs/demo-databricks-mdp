## ADDED Requirements

### Requirement: One replicable notebook
The patterns bundle SHALL hold one notebook,
`references/patterns/src/bronze_publish/bronze_publish_scd2_autocdc_history_migration_sql.py`,
that carries out steps 10 to 90 in order, with the target catalog and schema taken from
widgets, so it runs in another workspace by changing those widgets only.

#### Scenario: Run in a new schema
- **WHEN** the notebook runs with an empty schema named in the `schema` widget
- **THEN** steps 10 to 80 create the tables, the pipeline file and the pipeline in that
  schema and every step-80 check passes

#### Scenario: Re-run
- **WHEN** the notebook runs again in the same schema
- **THEN** step 55 reuses the existing pipeline instead of creating a second one

### Requirement: History loaded once without a stage table
`dim_asset_migrated` SHALL be a streaming table `STORED AS SCD TYPE 2`, keyed by `asset_id`,
whose history comes from a once-only flow reading the temporary view `asset_history` over
`asset_dim`. No table other than `asset_dim`, `asset_source` and `dim_asset_migrated` SHALL
be created.

#### Scenario: First update
- **WHEN** the pipeline runs for the first time
- **THEN** every `asset_dim` version is a version of `dim_asset_migrated` with
  `__START_AT` equal to its `start_date`, closed at the next version's `start_date`, and a
  retired asset's last version is closed at its `end_date`

#### Scenario: Later update
- **WHEN** the pipeline runs again without a full refresh
- **THEN** the history flow writes no rows and the history versions are unchanged

### Requirement: Live changes kept as SCD type 2
A second flow SHALL apply changes from the temporary view `asset_live`, a streaming read of
`asset_source`, to `dim_asset_migrated` with the same key and sequence column.

#### Scenario: New changes seeded
- **WHEN** step 60 appends changes to `asset_source` and the pipeline runs again
- **THEN** each change is a new open version starting at its `updated_at`, and the version
  it replaces is closed at that time

### Requirement: Results checked in the notebook
Step 80 SHALL check both rules above against the pipeline's event log and the table, print
one pass or fail line per check, and fail the cell when a check fails.

#### Scenario: Checks pass
- **WHEN** steps 10 to 70 ran as written
- **THEN** step 80 prints a pass line for "history not reloaded" and for "new changes added"

### Requirement: Clean removal
Step 90 SHALL run only when the `teardown` widget is `true`, and SHALL delete the pipeline
and drop the three tables and the hidden twin of `dim_asset_migrated`.

#### Scenario: Teardown
- **WHEN** step 90 runs with `teardown = true`
- **THEN** the pipeline and the four table slots are gone
