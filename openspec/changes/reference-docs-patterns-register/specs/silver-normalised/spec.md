## MODIFIED Requirements

### Requirement: Specs validated in CI
Every pull request touching the bundle, a normalised spec, the normalised
spec schema or the tests SHALL validate every
`src/layers/silver/normalised/specs/*.yml` against
`reference/docs/normalised-spec/schema.json` and run the unit tests, without
Databricks credentials.

#### Scenario: Invalid spec in a PR
- **WHEN** a PR adds a spec whose bridge declares both `explode` and
  `unpivot`
- **THEN** the PR's spec validation job fails
