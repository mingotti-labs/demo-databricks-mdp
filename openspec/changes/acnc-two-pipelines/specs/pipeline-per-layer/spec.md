## Purpose

Keeps each migrated source to one pipeline per medallion layer, and makes
the move from the older multi-pipeline layout safe: existing tables keep
their data and history, and no pipeline is removed while it still owns a
table.

## ADDED Requirements

### Requirement: One pipeline per layer per migrated source
A migrated source SHALL have exactly one bronze pipeline, publishing to
`bronze_<source>` and `bronze_<source>_publish`, and exactly one silver
pipeline, publishing to `silver_landing_<source>` and
`silver_normalised_<source>`. Tables SHALL keep their schemas and names.
acnc is the first migrated source.

#### Scenario: acnc after migration
- **WHEN** the bundle is validated for any target
- **THEN** acnc has two pipelines, `bronze--acnc--<target>` and
  `silver--acnc--<target>`, and every acnc table exists in the same schema
  under the same name as before

### Requirement: Existing tables move without data loss
Moving a table into another pipeline SHALL preserve its rows, including
every closed SCD2 version, and SHALL NOT trigger a full refresh. After the
move, a run with unchanged source data SHALL add no SCD2 versions.

#### Scenario: SCD2 history survives
- **WHEN** `charity_register_scd2` is moved into the bronze pipeline and
  that pipeline runs
- **THEN** its count of closed versions is at least the count before the
  move, and no version opened before the move is altered

#### Scenario: Unchanged source after the move
- **WHEN** the bronze pipeline runs twice after the move with no upstream
  change between the runs
- **THEN** the second run adds no SCD2 version

### Requirement: A pipeline is removed only when it owns no tables
A pipeline SHALL be removed from the bundle only after every table it owned
has been moved to another pipeline, so that deleting it drops no data.

#### Scenario: Emptied pipeline removed
- **WHEN** `acnc_charity_register_scd_modeling` is removed from the bundle
  after its tables were moved, and the bundle is deployed
- **THEN** the pipeline is deleted and `charity_register_scd1`/`_scd2`
  still exist with all their rows

### Requirement: No wrapper jobs
A job whose only purpose is to chain a unit's pipelines and steps for its
`run_<unit>` job SHALL NOT exist; `run_<unit>` SHALL hold those tasks
itself. A verification job SHALL exist only when it checks something no
other job checks; a check shared by sources SHALL be one job taking the
source as a parameter. Verification jobs SHALL be displayed as
`verify--<layer>--<source>--<target>` (or `verify--<layer>--<check>--<target>`
for a shared one).

#### Scenario: acnc jobs after migration
- **WHEN** the bundle is validated for any target
- **THEN** there is no `silver_acnc` job, acnc's own jobs are `run_acnc`
  and `verify_acnc_charity_register` (`verify--bronze--acnc--<target>`),
  and `run_acnc` verifies silver through the shared
  `verify_silver_normalised` job with `source: acnc`

### Requirement: A full refresh cannot discard SCD2 history
A full refresh of a bronze pipeline SHALL NOT truncate an SCD2 table.

#### Scenario: Full refresh requested
- **WHEN** a full refresh of the acnc bronze pipeline is requested
- **THEN** `charity_register_scd2` keeps all its rows, whether the refresh
  skips that table or the update is refused
