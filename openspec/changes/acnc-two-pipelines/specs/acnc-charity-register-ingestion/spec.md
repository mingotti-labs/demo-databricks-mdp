## MODIFIED Requirements

### Requirement: SCD1/SCD2 modeling, Python only
`charity_register_scd1` and `charity_register_scd2` SHALL exist in
`bronze_acnc_publish`, built by the acnc bronze pipeline (the same pipeline
that builds `charity_register_raw`) via `create_auto_cdc_from_snapshot_flow`
against the private `charity_register_valid` view (not
`charity_register_raw` directly, since NULL-ABN rows must be excluded
first), keyed by `ABN`. No SQL equivalent SHALL be built for this pattern.

#### Scenario: SCD tables match the valid (non-quarantined) row count on initial load
- **WHEN** the bronze pipeline is run and `charity_register_raw` and
  `charity_register_quarantine` are populated
- **THEN** `charity_register_scd1` and the current rows of
  `charity_register_scd2` each have a row count matching
  `charity_register_raw`'s row count minus `charity_register_quarantine`'s
  row count exactly

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`charity_register_raw` is populated and that `charity_register_scd1` and the
current rows of `charity_register_scd2` match `charity_register_raw` minus
`charity_register_quarantine`, chained into one job (`verify_bronze_acnc`,
displayed as `verify--bronze--acnc--<target>`) so the pattern can be
re-checked on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_bronze_acnc` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
