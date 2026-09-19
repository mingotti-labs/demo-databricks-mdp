## ADDED Requirements

### Requirement: Schema-evolution mode variants, both languages
For every `cloudFiles.schemaEvolutionMode` value (`addNewColumns`, `rescue`,
`failOnNewColumns`, `none`), a Lakeflow Declarative Pipeline SHALL exist in
both Python and SQL, each reading the same `s3_clickstream_raw` volume
landing path and each writing to its own distinct target table (not shared
with any other variant). Each variant's source SHALL document, in-code, that
mode's behavior and its error/recovery workflow.

#### Scenario: All eight variant pipelines are deployable
- **WHEN** the bundle is deployed to any target
- **THEN** eight pipelines exist for the clickstream Auto Loader pattern —
  four Python (`addNewColumns`/`rescue`/`failOnNewColumns`/`none`) and four
  SQL (the same four modes) — each targeting its own table

#### Scenario: Only the canonical variant is run as part of standing verification
- **WHEN** `verify_clickstream_pattern` (or any other CI-driven check) runs
- **THEN** only the `addNewColumns` (Python) pipeline is triggered; the other
  seven variants are validated as deployable but not executed

### Requirement: Documented behavior sourced from official docs where not independently verified
Documentation for `rescue`, `failOnNewColumns`, and `none` SHALL be sourced
from Databricks' own documentation and explicitly labeled as such, since only
`addNewColumns` was exercised against a real, live pipeline run in this
project.

#### Scenario: Non-canonical variant documentation is labeled
- **WHEN** any of the `rescue`, `failOnNewColumns`, or `none` source files is
  read
- **THEN** its header states the behavior is from Databricks' documentation,
  not independently re-verified via a live run here
