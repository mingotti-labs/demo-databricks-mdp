# pipeline-per-layer Specification

## Purpose
Keeps each migrated source to one pipeline per medallion layer, and makes
the move from the older multi-pipeline layout safe: existing tables keep
their data and history, and no pipeline is removed while it still owns a
table.

## Requirements

### Requirement: One pipeline per layer per source
Every source SHALL have exactly one bronze pipeline, publishing to
`bronze_<source>` and `bronze_<source>_publish`, displayed as
`bronze--<source>--<target>`, and exactly one silver pipeline, publishing
to `silver_landing_<source>`, displayed as `silver--<source>--<target>`.
A normalised source's `silver_normalised_<source>` tables are plain Delta
tables rebuilt by the `normalised` task of its `run_<source>` job.
Tables SHALL keep their schemas and names when a source is refactored to
this layout.

**Exceptions.** neon's bronze layer has two pipelines: its ingestion is a
managed Lakeflow Connect pipeline, which cannot hold transformation code,
so its SCD tables are built by one separate pipeline
(`neon_scd_modeling_python`). The `normalised` task keeps
`transformed_timestamp` on unchanged rows (openspec
`correct-platform-timestamps`).

**Exempt reference variants.** Resources kept only as documented reference
material, never part of a source's official flow, are outside this rule:
clickstream's seven non-canonical Auto Loader variants (displayed with
the source system `template`, e.g.
`bronze--template--autoloader--python--rescue--<target>`, tables unchanged
in `bronze_clickstream`), clickstream's SQL SCD pipeline, and neon's SQL
SCD pipeline and SQL SCD2 merge job. Only the Auto Loader pipeline that
feeds `bronze_clickstream_publish` (`clickstream_autoloader`) keeps the
source system `clickstream` among the Auto Loader pipelines; the SQL SCD
pipeline, which itself writes to `bronze_clickstream_publish`, keeps it
too.

#### Scenario: acnc after migration
- **WHEN** the bundle is validated for any target
- **THEN** acnc has two pipelines, `bronze--acnc--<target>` and
  `silver--acnc--<target>`, and every acnc table exists in the same schema
  under the same name as before its refactor

#### Scenario: ungm, iso, geonames and nsw_spatial after refactor
- **WHEN** the bundle is validated for any target
- **THEN** each of them has exactly `bronze--<source>--<target>` and
  `silver--<source>--<target>`, and every one of their tables exists in
  the same schema under the same name as before its refactor

#### Scenario: Source not on the pending list
- **WHEN** a source other than neon has more than one bronze or silver
  pipeline in its official flow
- **THEN** the layout is a defect

#### Scenario: Reference variant
- **WHEN** one of clickstream's seven non-canonical Auto Loader pipelines
  is listed in the workspace
- **THEN** its display name carries `template`, not `clickstream`, and it
  does not count against clickstream's one pipeline per layer

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
  and `run_acnc` verifies bronze and silver (when `verify` is true) through the
  shared `verify_bronze` and `verify_silver_normalised` jobs with `source: acnc`

### Requirement: A full refresh cannot discard SCD2 history
A full refresh of a bronze pipeline SHALL NOT truncate an SCD2 table.

#### Scenario: Full refresh requested
- **WHEN** a full refresh of the acnc bronze pipeline is requested
- **THEN** `charity_register_scd2` keeps all its rows, whether the refresh
  skips that table or the update is refused

### Requirement: Every source runs from its own run job
Every source SHALL have a `run_<source>` job holding its pipeline, verification
and `tag_patterns` tasks directly, so no source is left outside the
one-pipeline-per-layer layout.

#### Scenario: airroi, clickstream and neon after refactor
- **WHEN** the bundle is validated for any target
- **THEN** airroi and clickstream each have exactly `bronze--<source>--<target>`
  and `silver--<source>--<target>`, neon has its two bronze pipelines and
  `silver--neon--<target>`, each has a `run_<source>` job, no `silver_airroi`
  job exists, and every table keeps its schema and name

#### Scenario: Nothing pending
- **WHEN** the `pipeline-per-layer` and `silver-normalised` specs are read
- **THEN** no "Sources pending refactor" list names a source
