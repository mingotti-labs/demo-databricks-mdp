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
