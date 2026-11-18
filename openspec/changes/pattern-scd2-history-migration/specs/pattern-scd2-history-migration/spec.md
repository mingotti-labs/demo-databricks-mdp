## ADDED Requirements

### Requirement: Two replicable notebooks
The patterns bundle SHALL hold two notebooks in `references/patterns/src/bronze_publish/`:
`bronze_publish_scd2_autocdc_backfill_snapshot_sql.py` (live source: a materialized view)
and `bronze_publish_scd2_autocdc_backfill_stream_sql.py` (live source: an append-only
table). Each SHALL carry out its steps 10 to 90 in order, take the target catalog and schema
from widgets, and write its own pipeline file and create its own pipeline.

#### Scenario: Run in a new schema
- **WHEN** either notebook runs with an empty schema named in the `schema` widget
- **THEN** steps 10 to 80 create the tables, the pipeline file and the pipeline in that
  schema and every step-80 check passes

#### Scenario: Re-run
- **WHEN** a notebook runs again in the same schema
- **THEN** step 55 reuses the existing pipeline instead of creating a second one

### Requirement: History backfilled once without a stage table
`asset_dim_migrated` SHALL be a streaming table `STORED AS SCD TYPE 2`, keyed by `asset_id`,
whose history comes from a once-only backfill flow reading the temporary view
`asset_history` over `asset_dim_legacy`. No table other than the notebook's source tables,
`asset_dim_legacy` and `asset_dim_migrated` SHALL be created.

#### Scenario: First update
- **WHEN** the pipeline runs for the first time
- **THEN** every `asset_dim_legacy` row is a row of `asset_dim_migrated` with the same values,
  `__START_AT` equal to its `start_date` and `__END_AT` equal to its `end_date` (null when open)

#### Scenario: Later update
- **WHEN** the pipeline runs again without a full refresh
- **THEN** the backfill flow writes no rows and the backfilled versions are unchanged

### Requirement: Live changes from a materialized view
In the snapshot notebook, a snapshot flow with `WITH VERSION` SHALL apply the current state
of the materialized view `asset_source` (no timestamp column), read through the temporary
view `asset_live`, to `asset_dim_migrated`. The version SHALL change only when the view is
refreshed.

#### Scenario: View refreshed with changes
- **WHEN** step 60 changes, adds and deletes source rows, refreshes the view and the
  pipeline runs again
- **THEN** each changed or new asset has a new open version and each replaced or deleted
  version is closed, all at the view's refresh time

#### Scenario: Nothing refreshed
- **WHEN** the pipeline runs and the view was not refreshed since the last run
- **THEN** the snapshot flow processes no snapshot

### Requirement: Live changes from an append-only table
In the stream notebook, a streaming flow SHALL apply the rows appended to `asset_source` (no
timestamp column), read from its change data feed through the temporary view `asset_live`,
to `asset_dim_migrated`, sequenced by the commit time of each row.

#### Scenario: Rows appended
- **WHEN** step 60 appends rows and the pipeline runs again
- **THEN** each changed or new asset has a new open version starting at the row's commit
  time, and the version it replaces is closed at that time

#### Scenario: Unchanged row appended
- **WHEN** an appended row has the same values as the asset's open version
- **THEN** no new version is opened

### Requirement: Results checked in the notebook
Step 80 SHALL check that the backfill matches the legacy table, that the backfill did not run
again, and that the step-60 changes were applied, against the pipeline's event log and the
table; it SHALL print one pass or fail line per check and fail the cell when a check fails.

#### Scenario: Checks pass
- **WHEN** steps 10 to 70 ran as written
- **THEN** step 80 prints a pass line for each check

### Requirement: Clean removal
Step 90 SHALL run only when the `teardown` widget is `true`, and SHALL delete the notebook's
pipeline and drop its tables and their hidden twins.

#### Scenario: Teardown
- **WHEN** step 90 runs with `teardown = true`
- **THEN** the pipeline and all table slots of that notebook are gone
