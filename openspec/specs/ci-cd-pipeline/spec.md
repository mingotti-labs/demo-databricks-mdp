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
In the `standard` edition, a GitHub Actions workflow SHALL deploy the bundle
to the `tst` target when changes are merged to `main`, with no manual
approval required. The `free` edition has no `tst` target and no `tst` deploy
job; its `prd` deploy follows the merge directly, still gated by approval.

#### Scenario: Merge to main deploys to tst
- **WHEN** a pull request is merged into `main` and `edition` is `standard`
- **THEN** the workflow runs `databricks bundle deploy --target tst` without waiting for approval

#### Scenario: Merge to main skips tst (free)
- **WHEN** a pull request is merged into `main` and `edition` is `free`
- **THEN** no `tst` deploy runs and the `prd` deployment job waits for approval

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

### Requirement: Tst and prd deploys run the affected units
After a successful `tst` or `prd` deploy, the workflow SHALL run every
unit the `ci-affected-units` lookup reports for that target, one at a
time, comparing the deployed commit with the commit of that environment's
last successful deployment. The `dev`/PR flow SHALL NOT run units.

#### Scenario: Merge affecting acnc
- **WHEN** a merge to `main` changes acnc's bronze code and `tst` deploys
- **THEN** the `deploy-tst` job runs `run_acnc` against `tst` and waits for
  it to finish

#### Scenario: Merge affecting nothing runnable
- **WHEN** a merge deploys but the lookup reports no units
- **THEN** no job or pipeline is run and the deploy job succeeds

#### Scenario: Skipped prd deploy is not lost
- **WHEN** a prd approval is rejected for one merge and approved for the
  next
- **THEN** the approved prd run compares against the last successful prd
  deployment, so the rejected merge's affected units are run too

### Requirement: A failed unit run fails the deploy job
If any unit run fails, the environment's deploy job SHALL fail after the
remaining units have run, so the deployment is not recorded as successful
and the next deploy re-runs the failed unit.

#### Scenario: One unit fails
- **WHEN** two units are affected and the first one's run fails
- **THEN** the second still runs, and the job ends failed

### Requirement: Deploys do not overlap
Workflow runs that deploy and run units SHALL be serialised, so two merges
never run units at the same time.

#### Scenario: Two quick merges
- **WHEN** a second merge lands while the first merge's workflow is still
  running units
- **THEN** the second workflow waits until the first finishes
