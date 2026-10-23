## MODIFIED Requirements

### Requirement: Standing verification suite
The generic `verify_bronze` job, run by `run_airroi` when its `verify`
parameter is true and driven by `verification/bronze_checks/airroi.yml`,
SHALL check that both `_raw` tables are populated with the expected row
counts and expected columns (including the platform timestamp columns),
that both `_scd2` tables' row counts match their respective `_raw` tables,
and that the natural keys are unique, so the pattern can be re-checked on
demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `run_airroi` runs with `verify` set to true
- **THEN** `verify_bronze` completes successfully, or the job fails clearly
  at the check that found a problem
