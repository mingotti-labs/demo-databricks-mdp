## ADDED Requirements

### Requirement: airroi has no Silver Normalised layer
`airroi` SHALL stop at Silver Landing. No spec, job task or table for
`silver_normalised_airroi` SHALL exist.

#### Scenario: airroi runs
- **WHEN** `run_airroi` runs
- **THEN** it runs bronze, Silver Landing and `tag_patterns`, and creates no table in
  `silver_normalised_airroi`
