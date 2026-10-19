## ADDED Requirements

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
