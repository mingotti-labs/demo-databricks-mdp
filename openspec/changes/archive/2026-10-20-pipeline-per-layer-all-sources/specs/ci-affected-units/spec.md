## MODIFIED Requirements

### Requirement: A runnable unit is a run job
A runnable unit SHALL be a bundle job whose resource key starts with
`run_`. The unit's name is the rest of the key (`run_acnc` → `acnc`). The
lookup SHALL NOT depend on whether a unit is a source or a domain.

#### Scenario: Unit discovered from the bundle
- **WHEN** the bundle defines jobs `run_acnc`, `run_airroi`, and
  `verify_silver_normalised`
- **THEN** the units are `acnc` and `airroi`, and
  `verify_silver_normalised` is not a unit

### Requirement: Affected units are those whose run job reaches an affected resource
A unit SHALL be reported when its run job reaches an affected resource,
directly or through `run_job_task` chains, or when the run job itself is
affected.

#### Scenario: Reached through a nested job
- **WHEN** `verify_silver_normalised` is affected and `run_acnc` reaches it
  through a `run_job_task`
- **THEN** `acnc` is reported
