## MODIFIED Requirements

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`unspsc_public_raw` is populated and that `unspsc_public_scd1` and the
current rows of `unspsc_public_scd2` match its row count (closed SCD2
versions are history, not extra rows), run through the shared job `verify_bronze` with `source: ungm`, whose
checks are listed in `verification/bronze_checks/ungm.yml` so the pattern can be re-checked on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_bronze` is run with `source: ungm`
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
