## MODIFIED Requirements

### Requirement: Schema-evolution mode variants, both languages
For every `cloudFiles.schemaEvolutionMode` value (`addNewColumns`, `rescue`,
`failOnNewColumns`, `none`), a Lakeflow Declarative Pipeline SHALL exist in
both Python and SQL, each reading the same `s3_clickstream_raw` volume
landing path and each writing to its own distinct target table (not shared
with any other variant). Each variant's source SHALL document, in-code, that
mode's behavior and its error/recovery workflow. The canonical `addNewColumns`
(Python) pipeline SHALL be defined in the main bundle; the other seven SHALL be
defined in the patterns bundle (`references/patterns/`).

#### Scenario: All eight variant pipelines are deployable
- **WHEN** the main bundle and the patterns bundle are deployed to `dev`
- **THEN** eight pipelines exist for the clickstream Auto Loader pattern —
  four Python (`addNewColumns`/`rescue`/`failOnNewColumns`/`none`) and four
  SQL (the same four modes) — each targeting its own table, the canonical one
  from the main bundle and the other seven from the patterns bundle

#### Scenario: Only the canonical variant is run as part of standing verification
- **WHEN** `verify_clickstream_pattern` (or any other CI-driven check) runs
- **THEN** only the `addNewColumns` (Python) pipeline is triggered; the other
  seven variants are validated as deployable but not executed
