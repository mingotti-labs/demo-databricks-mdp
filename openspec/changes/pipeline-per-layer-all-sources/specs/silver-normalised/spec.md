## MODIFIED Requirements

### Requirement: One generic pipeline executes every normalised spec
Every normalised source SHALL be built by the same pipeline source file,
`src/layers/silver/normalised/pipeline.py`, included in that source's
silver pipeline (`silver--{source}--${bundle.target}`, see
`pipeline-per-layer`), which writes the normalised tables to
`silver_normalised_{source}` and receives the source's normalised spec
path through its configuration. No per-source transformation code SHALL
exist.

**Sources pending refactor** (each change that refactors a source removes
it from this list):
- airroi: `pipeline.py` runs in a separate pipeline,
  `silver--normalised--airroi--${bundle.target}`, next to its Landing
  pipeline.

#### Scenario: Adding a second source
- **WHEN** a second source is normalised
- **THEN** its change adds a normalised spec and bundle resources only,
  and `pipeline.py` is unchanged

### Requirement: Tags applied after every refresh
After each Silver Normalised refresh, a tag step SHALL set `mdp_layer`,
`mdp_source_system` and, for base, bridge and extracted entities,
`mdp_entity_kind` on every table the source's spec produces, using
`ALTER MATERIALIZED VIEW … SET TAGS`. The tag step is a task of the
source's `run_<source>` job that depends on the silver pipeline task.

**Sources pending refactor** (each change that refactors a source removes
it from this list):
- airroi: the tag step is a task of the wrapper job `silver_airroi`.

#### Scenario: Orchestrated run
- **WHEN** the `tag` task of `run_{source}` completes
- **THEN** every entity table in `silver_normalised_{source}` carries all
  three `mdp_*` tags with the values its spec implies

### Requirement: Per-source orchestration
A normalised source's Silver Landing and Silver Normalised datasets SHALL
be built in the same silver pipeline, so the pipeline's own dependency
graph orders Normalised after Landing and Normalised never reads a partial
Landing refresh. The source's `run_<source>` job SHALL run the silver
pipeline, then the tag step.

**Sources pending refactor** (each change that refactors a source removes
it from this list):
- airroi: Landing and Normalised are separate pipelines chained by the
  wrapper job `silver_airroi` (`landing` → `normalised` → `tag`).

#### Scenario: Landing refresh fails
- **WHEN** a Landing dataset fails during the silver pipeline update
- **THEN** the update fails, the Normalised datasets that read it are not
  refreshed, and the `tag` task does not run
