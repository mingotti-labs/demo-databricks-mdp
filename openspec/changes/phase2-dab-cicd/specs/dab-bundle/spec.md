## Purpose

Defines the Databricks Asset Bundle that deploys this repo's resources to the dev, tst, and prd catalogs of the single Free Edition workspace.

## ADDED Requirements

### Requirement: Bundle definition
A `databricks.yml` SHALL exist at the repo root defining the bundle and its `dev`, `tst`, and `prd` targets.

#### Scenario: Bundle file present and named
- **WHEN** the repo root is inspected
- **THEN** `databricks.yml` exists and declares a bundle name and the three targets

### Requirement: Targets share one workspace, differ by catalog
All three targets SHALL point at the same Databricks workspace host. Each target SHALL set its default catalog to `mdp_dev`, `mdp_tst`, or `mdp_prd` respectively, matching `CLAUDE.md`.

#### Scenario: Dev target resolves to mdp_dev
- **WHEN** `databricks bundle validate --target dev` runs
- **THEN** the resolved configuration shows the workspace host matching the platform's single workspace and the default catalog set to `mdp_dev`

#### Scenario: Tst and prd targets resolve to their catalogs
- **WHEN** `databricks bundle validate --target tst` and `--target prd` run
- **THEN** each resolves to the same workspace host with default catalog `mdp_tst` and `mdp_prd` respectively

### Requirement: Bundle validates cleanly
The bundle SHALL pass `databricks bundle validate` for all three targets with no errors.

#### Scenario: Validation succeeds for every target
- **WHEN** `databricks bundle validate --target <dev|tst|prd>` is run for each target
- **THEN** validation completes with no errors for all three
