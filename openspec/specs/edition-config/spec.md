# edition-config Specification

## Purpose
TBD - created by archiving change free-edition-config. Update Purpose after archive.

## Requirements

### Requirement: Edition declared in config.json
The repository SHALL have a root `config.json` with an `edition` key
(`free` or `standard`) and an `environments` key listing the targets that
edition deploys. The `standard` edition SHALL behave exactly as the
repository did before this file existed.

#### Scenario: Free edition configuration
- **WHEN** `config.json` contains `"edition": "free"`
- **THEN** `environments` is `["dev", "prd"]` and the bundle defines no `tst` target

### Requirement: Edition-specific files live under cicd
Everything that differs by edition SHALL live in `cicd/workflows/<edition>/`
and `cicd/databricks/<edition>.yml`. Pipeline, job, and source code SHALL NOT
branch on the edition.

#### Scenario: Pipeline code is edition-agnostic
- **WHEN** the edition changes from `standard` to `free`
- **THEN** no file under `src/` or `resources/` changes

### Requirement: Applying an edition
`cicd/apply_edition.py` SHALL read `config.json` and copy
`cicd/workflows/<edition>/*` to `.github/workflows/` and
`cicd/databricks/<edition>.yml` to the root `databricks.yml`, and do nothing
else. The generated files SHALL be committed.

#### Scenario: Switching edition
- **WHEN** `edition` is changed and `apply_edition.py` is run
- **THEN** `.github/workflows/` and the root `databricks.yml` match that edition's files in `cicd/`

### Requirement: Generated files cannot drift
A pull request check SHALL run `apply_edition.py --check` and fail when the
generated files differ from what the script would produce.

#### Scenario: Hand edit of a generated file
- **WHEN** a pull request edits the root `databricks.yml` without editing the `cicd/` source
- **THEN** the drift check fails
