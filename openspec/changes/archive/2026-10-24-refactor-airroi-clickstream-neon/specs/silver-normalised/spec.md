## RENAMED Requirements

- FROM: `### Requirement: One generic pipeline executes every normalised spec`
- TO: `### Requirement: One generic job task executes every normalised spec`

## MODIFIED Requirements

### Requirement: One generic job task executes every normalised spec
Every normalised source SHALL be built by the same task source file,
`src/layers/silver/normalised/rebuild.py`, run as the `normalised` task of
the source's `run_<source>` job after its silver pipeline. The task writes
the normalised tables to `silver_normalised_{source}` and receives the
source's normalised spec path through its parameters. No per-source
transformation code SHALL exist.

#### Scenario: Adding a second source
- **WHEN** a second source is normalised
- **THEN** its change adds a normalised spec and bundle resources only,
  and `rebuild.py` is unchanged

### Requirement: Tags applied after every refresh
After each Silver Normalised refresh, a tag step SHALL set `mdp_layer`,
`mdp_source_system` and, for base, bridge and extracted entities,
`mdp_entity_kind` on every table the source's spec produces, using
`ALTER MATERIALIZED VIEW … SET TAGS`. The tag step is a task of the
source's `run_<source>` job that depends on the silver pipeline task.

#### Scenario: Orchestrated run
- **WHEN** the `tag` task of `run_{source}` completes
- **THEN** every entity table in `silver_normalised_{source}` carries all
  three `mdp_*` tags with the values its spec implies

### Requirement: Per-source orchestration
A normalised source's Silver Landing SHALL be built by its silver pipeline
and its Silver Normalised tables by the `normalised` task of its
`run_<source>` job, which depends on the silver pipeline task, so
Normalised never reads a partial Landing refresh. The job SHALL then run
the tag step.

#### Scenario: Landing refresh fails
- **WHEN** a Landing dataset fails during the silver pipeline update
- **THEN** the update fails, the `normalised` task does not run, and the
  `tag` task does not run
