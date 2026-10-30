## MODIFIED Requirements

### Requirement: Silver Landing
For each dataset, `silver_landing.portfolio__<dataset>` SHALL be built by the
source's silver pipeline from the SCD2 change feed with `land_changes`, keyed by
the dataset's natural key.

#### Scenario: Landing matches Bronze Publish
- **WHEN** the silver pipeline has run
- **THEN** each Landing table's current rows equal its SCD2 table's current rows
