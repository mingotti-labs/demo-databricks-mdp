## MODIFIED Requirements

### Requirement: SCD1/SCD2 modeling, Python only
`unspsc_public_scd1` and `unspsc_public_scd2` SHALL exist in
`bronze_ungm_publish`, built by the source's bronze pipeline (`bronze--ungm--<target>`, the same pipeline that builds its `_raw` tables) via
`create_auto_cdc_from_snapshot_flow`
against `unspsc_public_raw` directly — not streaming Auto CDC, since this
source is not append-only, and not an intermediate snapshot materialized
view, which is unnecessary (confirmed via a real run against Neon's
equivalent pattern). No SQL equivalent SHALL be built for this pattern.

#### Scenario: SCD tables match source row count on initial load
- **WHEN** the bronze pipeline is run after `unspsc_public_raw` is populated
- **THEN** `unspsc_public_scd1` and the current rows (`__END_AT IS NULL`)
  of `unspsc_public_scd2` each have a row count matching
  `unspsc_public_raw` exactly

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`unspsc_public_raw` is populated and that `unspsc_public_scd1` and the
current rows of `unspsc_public_scd2` match its row count (closed SCD2
versions are history, not extra rows), chained into one job
(`verify_unspsc_pattern`, displayed as
`verify--bronze--ungm--<target>`) so the pattern can be re-checked on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_unspsc_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
