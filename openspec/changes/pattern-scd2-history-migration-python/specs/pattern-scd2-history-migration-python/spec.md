## ADDED Requirements

### Requirement: One module configured with three SQL strings
The patterns bundle SHALL hold `references/patterns/src/common/scd2_migration.py` with
`migrate_and_load(target, keys, history_sql, live_sql, live_version_sql, technical_columns, sid)`.
All version, cut-over, row selection and key logic SHALL live in this module; a pipeline file SHALL
only import it and call `migrate_and_load`.

#### Scenario: Custom live logic
- **WHEN** `live_sql` is a `SELECT` with a join and a filter
- **THEN** the pipeline loads the rows that `SELECT` returns, with no change to the module

#### Scenario: Missing column
- **WHEN** `history_sql` returns no `valid_to` column
- **THEN** the pipeline fails at start-up with a message naming the missing column

### Requirement: Same results as the SQL notebooks
For each variant (`plain`, `sid`, `sid_unique`) the Python notebook SHALL produce the same
`asset_dim_migrated` (and, for `sid_unique`, the same one-key-per-version view) as the SQL notebook
of that variant on the same seed data.

#### Scenario: Plain variant
- **WHEN** the notebook runs with `variant = plain`
- **THEN** the SQL snapshot notebook's step-80 checks pass

#### Scenario: Key variants
- **WHEN** the notebook runs with `variant = sid` or `sid_unique`
- **THEN** the step-80 checks of `..._snapshot_sid_sql` or `..._snapshot_sid_unique_sql` pass

### Requirement: Technical columns never open a version
Columns named in `technical_columns` SHALL be excluded from `row_hash` and from history tracking,
and SHALL still be written to the target.

#### Scenario: Load timestamp changes
- **WHEN** a live row is unchanged except for its `ingested_timestamp`
- **THEN** no new version is opened and the key is unchanged

### Requirement: A skill writes the pipeline file
`references/skills/bronze-publish-scd2-autocdc-backfill-snapshot-python/` SHALL write the pipeline
file (import and `migrate_and_load` call) from its inputs.

#### Scenario: Skill output runs as-is
- **WHEN** the skill's output for the notebook's tables is loaded into a scratch pipeline
- **THEN** its table equals the notebook's `asset_dim_migrated`
