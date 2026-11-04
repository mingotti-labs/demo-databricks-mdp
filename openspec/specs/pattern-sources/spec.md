# pattern-sources Specification

## Purpose
TBD - created by archiving change neon-clickstream-to-patterns. Update Purpose after archive.

## Requirements

### Requirement: neon and clickstream are deployable patterns
The patterns bundle (`references/patterns/`) SHALL hold the Lakeflow Connect query-based
PostgreSQL pipeline (`pattern_bronze_lakeflow_query_postgresql`) and the canonical Auto
Loader pipeline (`pattern_bronze_autoloader_add_new_columns_python`), each with its seed or
generator job and a verify job, writing only to `pattern_bronze`. The main bundle SHALL
define no neon or clickstream resource.

#### Scenario: Main bundle validated
- **WHEN** the main bundle is validated for any target
- **THEN** no pipeline or job names neon or clickstream

#### Scenario: Patterns bundle validated
- **WHEN** the patterns bundle is validated
- **THEN** both pattern pipelines and their jobs are present

#### Scenario: Pattern run
- **WHEN** a human deploys the patterns bundle, seeds or generates data and runs a pattern
  pipeline followed by its verify job
- **THEN** the verify job passes against the `pattern_bronze` tables

### Requirement: Patterns do not read main-bundle tables
No pattern SHALL read a table that the main bundle creates; a pattern that needs a source
table SHALL read another pattern's table.

#### Scenario: Dependent patterns
- **WHEN** `bronze_publish_scd1_autocdc_stream_sql`, `bronze_publish_scd1_materialized_view_sql`
  or `bronze_publish_scd2_merge_sql` runs
- **THEN** it reads `pattern_bronze.autoloader_add_new_columns_python` or
  `pattern_bronze.lakeflow_query_postgresql_customers`

### Requirement: Deploy instructions
`references/patterns/README.md` SHALL give, per pattern, the commands to deploy, seed or
generate, run, verify, destroy and drop the tables a destroy leaves, and the table slots
the pattern uses while deployed.

#### Scenario: Freeing slots after a look
- **WHEN** the README's remove steps are followed
- **THEN** no `pattern_bronze` table, hidden twin or event log of the pattern remains

### Requirement: Patterns bundle is validated in CI
Every pull request SHALL run `databricks bundle validate` for the patterns bundle; CI SHALL
NOT deploy it.

#### Scenario: Broken pattern resource
- **WHEN** a pull request leaves a patterns-bundle resource invalid
- **THEN** the PR check fails
