## MODIFIED Requirements

### Requirement: Source-aligned table per Bronze Publish entity
For every entity Bronze Publish exposes at least one SCD object for, there
SHALL be exactly one corresponding Silver Landing table, in the one schema `silver_landing`, named `{source_system}__{entity}`: the
source system, a double underscore, and the entity's datasource name (not
the Bronze Publish object's SCD-suffixed name). The standard edition keeps
one schema per source, `silver_landing_{source_system}`, with the table named
`{entity}`.

#### Scenario: Entity published to Bronze Publish
- **WHEN** a Bronze Publish schema contains at least one SCD object for an
  entity
- **THEN** `silver_landing` contains a table named
  `{source_system}__{entity}`

#### Scenario: Two sources share the schema
- **WHEN** `acnc` and `nsw_spatial` both have Landing tables
- **THEN** their tables are `silver_landing.acnc__charity_register` and
  `silver_landing.nsw_spatial__property`, and each source's design-pattern
  tag step tags only tables starting with its own `{source_system}__`
