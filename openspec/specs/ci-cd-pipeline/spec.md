# ci-cd-pipeline Specification

## Purpose
Automates bundle validation and gated deployment through GitHub Actions, so every change ships the same way instead of by hand.

## Requirements

### Requirement: Validation on pull request
A GitHub Actions workflow SHALL run `databricks bundle validate` on every pull request.

#### Scenario: PR triggers validation
- **WHEN** a pull request is opened or updated against `main`
- **THEN** the validation workflow runs `databricks bundle validate` and the PR check reflects its pass/fail result

### Requirement: Dev deploy on pull request
A GitHub Actions workflow SHALL deploy the bundle to the `dev` target on every pull request, with no manual approval required.

#### Scenario: PR deploys to dev automatically
- **WHEN** a pull request is opened or updated against `main`
- **THEN** the workflow runs `databricks bundle deploy --target dev` without waiting for approval

### Requirement: Tst deploy on merge to main
A GitHub Actions workflow SHALL deploy the bundle to the `tst` target when changes are merged to `main`, with no manual approval required.

#### Scenario: Merge to main deploys to tst
- **WHEN** a pull request is merged into `main`
- **THEN** the workflow runs `databricks bundle deploy --target tst` without waiting for approval

### Requirement: Prd deploy gated by manual approval
A GitHub Actions workflow SHALL deploy the bundle to the `prd` target when changes are merged to `main`, but SHALL wait for a manual approval before running.

#### Scenario: Merge to main pauses for approval before prd deploy
- **WHEN** a pull request is merged into `main`
- **THEN** the `prd` deployment job waits in a pending state for a required reviewer to approve the GitHub Environment before `databricks bundle deploy --target prd` runs

#### Scenario: Rejected approval blocks prd deploy
- **WHEN** a required reviewer rejects the pending `prd` deployment
- **THEN** `databricks bundle deploy --target prd` does not run and the workflow run is marked failed or cancelled

### Requirement: No long-lived personal credentials in CI
Databricks authentication used by `bundle deploy` in CI SHALL be a service-principal OAuth machine-to-machine credential or a scoped personal access token, stored only as a GitHub Actions secret — never a long-lived personal token committed to the repo or hardcoded in workflow files.

#### Scenario: Deploy workflow reads credentials from secrets
- **WHEN** any deploy workflow authenticates to Databricks
- **THEN** it reads the client ID/secret or PAT from a GitHub Actions secret, and no credential value appears in the workflow YAML or repo history
