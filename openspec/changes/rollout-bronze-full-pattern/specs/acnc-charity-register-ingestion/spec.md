## MODIFIED Requirements

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`charity_register_raw` is populated and that `charity_register_scd1` and the
current rows of `charity_register_scd2` match `charity_register_raw` minus
`charity_register_quarantine`, run through the shared job `verify_bronze` with `source: acnc`, whose
checks are listed in `verification/bronze_checks/acnc.yml` so the pattern can be re-checked on
demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_bronze` is run with `source: acnc`
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
