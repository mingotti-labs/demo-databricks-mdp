## MODIFIED Requirements

### Requirement: Silver Landing
`silver_landing.wikipedia__sp500_constituents` SHALL be built by the source's
silver pipeline from the SCD2 table's change feed (`land_changes`), with
`symbol` as the natural key and the platform conventions of Silver Landing.

#### Scenario: Landing matches Bronze Publish
- **WHEN** the silver pipeline has run
- **THEN** Landing has one row per SCD2 version and its current rows equal the
  SCD2 table's current rows
