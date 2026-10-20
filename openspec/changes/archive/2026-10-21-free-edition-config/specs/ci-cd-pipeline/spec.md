## MODIFIED Requirements

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
