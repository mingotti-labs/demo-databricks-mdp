## MODIFIED Requirements

### Requirement: Silver Landing
`silver_landing.yahoo__<dataset>` SHALL be built from each Bronze Publish change
feed with `land_changes`, keyed by the same natural keys.

#### Scenario: Landing matches Bronze Publish
- **WHEN** the silver pipeline has run
- **THEN** each Landing table's current rows equal its Bronze Publish table's
  current rows
