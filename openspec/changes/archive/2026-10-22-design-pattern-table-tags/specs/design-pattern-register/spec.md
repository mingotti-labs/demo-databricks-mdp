## ADDED Requirements

### Requirement: Tables carry their design pattern as a tag
Every table that uses a design pattern, live or pattern-only, SHALL
carry the Unity Catalog tag `design_pattern`, whose value is the ID of the
register entry that defines how the table is built. The tag SHALL be set by a
step in the source's run job (or the patterns bundle's tag job), after the last pipeline task, and SHALL be
idempotent.

#### Scenario: Reading a table's pattern
- **WHEN** a reader looks up a published table's tags in Unity Catalog
- **THEN** `design_pattern` is a heading in `references/docs/registers/design-patterns.md`

#### Scenario: Unknown pattern ID
- **WHEN** the mapping names an ID that is not a register heading
- **THEN** the test suite fails
