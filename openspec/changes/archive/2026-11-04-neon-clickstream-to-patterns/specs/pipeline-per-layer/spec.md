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

**Not sources of the main bundle.** neon and clickstream are reference patterns in
the patterns bundle (`references/patterns/`, openspec `neon-clickstream-to-patterns`),
displayed with the source system `pattern`, and are outside this rule, as is every
other pattern there. The `normalised` task keeps `transformed_timestamp` on unchanged
rows (openspec `correct-platform-timestamps`).

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
- **WHEN** a source of the main bundle has more than one bronze or silver
  pipeline in its official flow
- **THEN** the layout is a defect

#### Scenario: Reference variant
- **WHEN** a patterns-bundle pipeline is listed in the workspace
- **THEN** its display name carries `pattern` and it does not count against
  any source's one pipeline per layer

### Requirement: Every source runs from its own run job
Every source SHALL have a `run_<source>` job holding its pipeline, verification
and `tag_patterns` tasks directly, so no source is left outside the
one-pipeline-per-layer layout.

#### Scenario: airroi, clickstream and neon after refactor
- **WHEN** the bundle is validated for any target
- **THEN** airroi has exactly `bronze--airroi--<target>` and `silver--airroi--<target>`,
  a `run_airroi` job, no `silver_airroi` job exists, every table keeps its schema
  and name, and no `run_neon` or `run_clickstream` job exists

#### Scenario: Nothing pending
- **WHEN** the `pipeline-per-layer` and `silver-normalised` specs are read
- **THEN** no "Sources pending refactor" list names a source
