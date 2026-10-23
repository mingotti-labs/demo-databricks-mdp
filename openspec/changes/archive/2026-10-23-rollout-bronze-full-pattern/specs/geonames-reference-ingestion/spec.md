## MODIFIED Requirements

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that all four
`_raw` tables are populated with their expected row counts and carry
`ingested_timestamp`, and that every table's `_scd2` current-row count
matches its expected source count — run through the shared job `verify_bronze` with `source: geonames`, whose
checks are listed in `verification/bronze_checks/geonames.yml`.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_bronze` is run with `source: geonames`
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
