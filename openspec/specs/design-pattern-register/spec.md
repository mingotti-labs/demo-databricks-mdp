# design-pattern-register Specification

## Purpose
TBD - created by archiving change reference-docs-patterns-register. Update Purpose after archive.

## Requirements

### Requirement: Design patterns are registered
`references/docs/registers/design-patterns.md` SHALL list every design pattern
implemented in this repository, one entry per pattern, identified by a
technology-driven ID of the form `<layer>_<technology>_<variant>_<language>`
(language last, omitted when the pattern is language-agnostic). Each entry
SHALL state what the pattern is, when to use it, where its code lives, which
data sources use it, and whether it was verified against real data or only
documented.

#### Scenario: Looking up a pattern
- **WHEN** a reader opens the register
- **THEN** each pattern's ID, purpose, code location, sources and verification status are on its entry

#### Scenario: Pattern with no code in the repo
- **WHEN** a pattern is an alternative to one the repo uses (for example the other Lakeflow Connect architectures) and has no code here
- **THEN** it has an entry with code "none" and evidence `documented only`

#### Scenario: Pattern split by behaviour
- **WHEN** two implementations behave differently for the same step (for example streaming and snapshot-based Auto CDC)
- **THEN** they are separate entries with separate IDs

### Requirement: Data sources link to their patterns
Each source in `references/docs/registers/data-sources.md` SHALL list the
design-pattern IDs it uses, each linking to its entry in the register.

#### Scenario: Source to pattern
- **WHEN** a reader opens a source's entry in the data-sources register
- **THEN** its "Design patterns" line links every pattern the source uses

### Requirement: Reference documentation lives under references/docs
The repository's documentation SHALL live under `references/docs/`, and no
tracked file outside `openspec/changes/archive/` SHALL refer to a `docs/`
path that no longer exists.

#### Scenario: No stale documentation paths
- **WHEN** the repository is searched for `docs/` paths outside `references/` and the archive
- **THEN** no reference to the old location remains

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
