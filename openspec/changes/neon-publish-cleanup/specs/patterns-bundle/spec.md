## ADDED Requirements

### Requirement: The snapshot SCD2 pattern is a reference in the patterns bundle
`references/patterns/` SHALL hold the snapshot-based Auto CDC SCD2 pattern as
`bronze_publish_scd2_autocdc_snapshot_python`: a pipeline source file, a
pipeline resource displayed as
`bronze--pattern--publish--scd2--snapshot--python--<target>`, writing to
`pattern_bronze_publish`, and a design pattern register entry that points to it
and keeps the findings from Neon: streaming Auto CDC fails against an upserted
source, `skipChangeCommits` silently drops updated rows, and switching a flow's
source after its first run can add spurious versions. The pattern SHALL be
reference only: it is deployed to dev by the patterns bundle and never run, so it
holds no table.

#### Scenario: The pattern is recoverable without Neon
- **WHEN** the Neon Bronze Publish code is removed from the main bundle
- **THEN** the patterns bundle still holds the snapshot SCD2 flow and the register
  entry still names where its code is

#### Scenario: Not part of the main bundle
- **WHEN** the main bundle is validated for any target
- **THEN** no resource named for the new pattern appears among its resources
