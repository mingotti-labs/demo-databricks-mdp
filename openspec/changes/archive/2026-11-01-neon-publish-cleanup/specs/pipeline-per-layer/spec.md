## MODIFIED Requirements

### Requirement: One pipeline per layer per source
Every source SHALL have exactly one bronze pipeline, publishing to
`bronze_<source>` and `bronze_<source>_publish`, displayed as
`bronze--<source>--<target>`, and exactly one silver pipeline, publishing
to `silver_landing` (tables `<source>__<entity>`), displayed as `silver--<source>--<target>`.
A normalised source's `silver_normalised_<source>` tables are plain Delta
tables rebuilt by the `normalised` task of its `run_<source>` job.
Tables SHALL keep their schemas and names when a source is refactored to
this layout; Silver Landing tables moved once, from `silver_landing_<source>`
to `silver_landing.<source>__<entity>` (openspec
`single-silver-landing-schema`), keeping the pipelines' keys and display names.

**Exceptions.** neon has only its managed Lakeflow Connect ingestion pipeline
(`bronze--neon--<target>`) and no silver pipeline: its Bronze Publish and Silver
Landing tables were removed to free table slots (openspec
`neon-publish-cleanup`, backup in `references/backups/neon/`). The `normalised`
task keeps `transformed_timestamp` on unchanged rows (openspec
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
  `silver--acnc--<target>`, and every acnc bronze and Silver Normalised table
  exists in the same schema under the same name as before its refactor

#### Scenario: ungm, iso, geonames and nsw_spatial after refactor
- **WHEN** the bundle is validated for any target
- **THEN** each of them has exactly `bronze--<source>--<target>` and
  `silver--<source>--<target>`, and every one of their bronze tables exists
  in the same schema under the same name as before its refactor

#### Scenario: Source not on the pending list
- **WHEN** a source other than neon has more than one bronze or silver
  pipeline in its official flow
- **THEN** the layout is a defect

#### Scenario: Reference variant
- **WHEN** one of clickstream's seven non-canonical Auto Loader pipelines
  is listed in the workspace
- **THEN** its display name carries `template`, not `clickstream`, and it
  does not count against clickstream's one pipeline per layer

### Requirement: Every source runs from its own run job
Every source SHALL have a `run_<source>` job holding its pipeline, verification
and `tag_patterns` tasks directly, so no source is left outside the
one-pipeline-per-layer layout.

#### Scenario: airroi, clickstream and neon after refactor
- **WHEN** the bundle is validated for any target
- **THEN** airroi and clickstream each have exactly `bronze--<source>--<target>`
  and `silver--<source>--<target>`, neon has only its Lakeflow Connect ingestion
  pipeline, each has a `run_<source>` job, no `silver_airroi` job exists, and
  every table keeps its schema and name

#### Scenario: Nothing pending
- **WHEN** the `pipeline-per-layer` and `silver-normalised` specs are read
- **THEN** no "Sources pending refactor" list names a source
