## MODIFIED Requirements

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum): both `_raw`
tables are populated with their expected row counts and carry
`ingested_timestamp`; `subdivision_codes_quarantine` is non-empty and
`raw = distinct_key_count + quarantine_count`; both SCD2 tables' current-row
counts match their expected source count — run through the shared job `verify_bronze` with `source: iso`, whose
checks are listed in `verification/bronze_checks/iso.yml`.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_bronze` is run with `source: iso`
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
