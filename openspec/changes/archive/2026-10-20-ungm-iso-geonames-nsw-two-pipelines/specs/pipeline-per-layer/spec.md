## MODIFIED Requirements

### Requirement: One pipeline per layer per source
Every source SHALL have exactly one bronze pipeline, publishing to
`bronze_<source>` and `bronze_<source>_publish`, displayed as
`bronze--<source>--<target>`, and exactly one silver pipeline, publishing
to `silver_landing_<source>` and, once the source is normalised,
`silver_normalised_<source>`, displayed as `silver--<source>--<target>`.
Tables SHALL keep their schemas and names when a source is refactored to
this layout.

**Exceptions.** neon's bronze layer has two pipelines: its ingestion is a
managed Lakeflow Connect pipeline, which cannot hold transformation code,
so its SCD tables are built by one separate pipeline
(`neon_scd_modeling_python`).

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

**Sources pending refactor** (each change that refactors a source removes
it from this list):
- airroi: bronze ingestion + SCD pipelines to merge; Silver Landing +
  Silver Normalised pipelines to merge.
- clickstream: the canonical Auto Loader pipeline and the Python SCD
  pipeline to merge; silver pipeline to display as
  `silver--clickstream--<target>`.
- neon: silver pipeline to display as `silver--neon--<target>`.

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
  pipeline in its official flow and is not listed as pending refactor
- **THEN** the layout is a defect, not known pending work

#### Scenario: Reference variant
- **WHEN** one of clickstream's seven non-canonical Auto Loader pipelines
  is listed in the workspace
- **THEN** its display name carries `template`, not `clickstream`, and it
  does not count against clickstream's one pipeline per layer

### Requirement: No wrapper jobs
A job whose only purpose is to chain a unit's pipelines and steps for its
`run_<unit>` job SHALL NOT exist; `run_<unit>` SHALL hold those tasks
itself. A verification job SHALL exist only when it checks something no
other job checks; a check shared by sources SHALL be one job taking the
source as a parameter. Verification jobs SHALL be displayed as
`verify--<layer>--<source>--<target>` (or `verify--<layer>--<check>--<target>`
for a shared one).

**Sources pending refactor** (each change that refactors a source removes
it from this list):
- airroi: wrapper job `silver_airroi` to remove.

#### Scenario: acnc jobs after migration
- **WHEN** the bundle is validated for any target
- **THEN** there is no `silver_acnc` job, acnc's own jobs are `run_acnc`
  and `verify_acnc_charity_register` (`verify--bronze--acnc--<target>`),
  and `run_acnc` verifies silver through the shared
  `verify_silver_normalised` job with `source: acnc`
