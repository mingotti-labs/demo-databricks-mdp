## MODIFIED Requirements

### Requirement: SCD1/SCD2 modeling, Python only
`property_scd1` and `property_scd2` SHALL exist in
`bronze_nsw_spatial_publish`, built by the source's bronze pipeline (`bronze--nsw_spatial--<target>`, the same pipeline that builds its `_raw` tables) via
`create_auto_cdc_from_snapshot_flow`
against `property_raw` directly, keyed by `addressstringoid` — not `propid`,
which is shared across every address within the same property (a unit
block has one row per unit, all sharing one `propid`), confirmed via a real
run before this key was finalized. No SQL equivalent SHALL be built for
this pattern.

#### Scenario: SCD tables match source row count on initial load
- **WHEN** the bronze pipeline is run after `property_raw` is populated
- **THEN** `property_scd1` and the current rows (`__END_AT IS NULL`) of
  `property_scd2` each have a row count matching `property_raw` exactly

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`property_raw` is populated and that `property_scd1` and the current rows
of `property_scd2` match its row count exactly (closed SCD2 versions are
history, not extra rows), chained into one job
(`verify_nsw_property_pattern`, displayed as
`verify--bronze--nsw_spatial--<target>`) so the pattern can be re-checked on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_nsw_property_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
