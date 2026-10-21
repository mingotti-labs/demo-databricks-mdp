## ADDED Requirements

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
