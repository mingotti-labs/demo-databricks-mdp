## MODIFIED Requirements

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`property_raw` is populated and that `property_scd1` and the current rows
of `property_scd2` match its row count exactly (closed SCD2 versions are
history, not extra rows), run through the shared job `verify_bronze` with `source: nsw_spatial`, whose
checks are listed in `verification/bronze_checks/nsw_spatial.yml` so the pattern can be re-checked on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_bronze` is run with `source: nsw_spatial`
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
