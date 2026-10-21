## ADDED Requirements

### Requirement: Design patterns are registered
`reference/docs/registers/design-patterns.md` SHALL list every design pattern
implemented in this repository, one entry per pattern, identified by a
technology-driven ID of the form `<layer>_<technology>_<variant>_<language>`
(language last, omitted when the pattern is language-agnostic). Each entry
SHALL state what the pattern is, when to use it, where its code lives, which
data sources use it, and whether it was verified against real data or only
documented.

#### Scenario: Looking up a pattern
- **WHEN** a reader opens the register
- **THEN** each pattern's ID, purpose, code location, sources and verification status are on its entry

#### Scenario: Pattern split by behaviour
- **WHEN** two implementations behave differently for the same step (for example streaming and snapshot-based Auto CDC)
- **THEN** they are separate entries with separate IDs

### Requirement: Data sources link to their patterns
Each source in `reference/docs/registers/data-sources.md` SHALL list the
design-pattern IDs it uses, each linking to its entry in the register.

#### Scenario: Source to pattern
- **WHEN** a reader opens a source's entry in the data-sources register
- **THEN** its "Design patterns" line links every pattern the source uses

### Requirement: Reference documentation lives under reference/docs
The repository's documentation SHALL live under `reference/docs/`, and no
tracked file outside `openspec/changes/archive/` SHALL refer to a `docs/`
path that no longer exists.

#### Scenario: No stale documentation paths
- **WHEN** the repository is searched for `docs/` paths outside `reference/` and the archive
- **THEN** no reference to the old location remains
