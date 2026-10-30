## MODIFIED Requirements

### Requirement: Silver Landing
`silver_landing.sec__company_tickers` and `silver_landing.sec__company_facts`
SHALL be built from the SCD2 change feeds with `land_changes`, keyed by the
same natural keys.

#### Scenario: Landing matches Bronze Publish
- **WHEN** the silver pipeline has run
- **THEN** each Landing table's current rows equal its SCD2 table's current rows
