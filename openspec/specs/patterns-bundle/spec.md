# patterns-bundle Specification

## Purpose
TBD - created by archiving change references-patterns-bundle. Update Purpose after archive.

## Requirements

### Requirement: Pattern-only implementations live in a separate bundle
Implementations that exist only to demonstrate a design pattern SHALL be
defined in a bundle rooted at `references/patterns/`, with its own
`databricks.yml`, `resources/` and `src/`, and a `dev` target only. The main
bundle SHALL NOT include its resources.

#### Scenario: Patterns bundle has no prd target
- **WHEN** `references/patterns/databricks.yml` is read
- **THEN** it defines a `dev` target and no `tst` or `prd` target

#### Scenario: Main bundle does not deploy pattern resources
- **WHEN** the main bundle is validated for any target
- **THEN** none of the moved pattern pipelines appears among its resources

### Requirement: Main bundle does not sync references
The main bundle SHALL exclude `references/**` from its workspace sync, in every
edition.

#### Scenario: References not uploaded
- **WHEN** the main bundle is deployed
- **THEN** no file under `references/` is uploaded to the target workspace

### Requirement: Pattern pipelines are named as patterns
Pattern-only pipelines SHALL use the source-system segment `pattern` in their
display names, not `template`.

#### Scenario: Display name
- **WHEN** a moved Auto Loader variant is deployed
- **THEN** its name is `bronze--pattern--autoloader--<language>--<mode>--<target>`

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
