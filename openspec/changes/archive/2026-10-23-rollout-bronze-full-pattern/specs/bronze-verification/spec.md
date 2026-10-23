## ADDED Requirements

### Requirement: One parameterised bronze verification
Bronze verification SHALL be one job and one notebook that take the source as a
parameter and read that source's checks from a spec file under
`verification/bronze_checks/`. Adding a source SHALL need a spec file and no new
job or notebook.

#### Scenario: Checking one source
- **WHEN** the job runs with `source = iso`
- **THEN** it checks every table listed in `iso.yml` and fails naming the table
  and the rule that failed

### Requirement: Verification is opt-in
A `run_<unit>` job SHALL run its verification tasks only when its `verify`
parameter is `"true"`, and the parameter SHALL default to `"false"`. Turning
verification off SHALL NOT skip any other task.

#### Scenario: Default run
- **WHEN** CI runs `run_<unit>` without parameters
- **THEN** the bronze and silver verification tasks are excluded, and the
  pipelines and notebooks around them run

#### Scenario: Verified run
- **WHEN** `run_<unit>` runs with `verify = true`
- **THEN** the bronze verification runs after the bronze pipeline and before
  silver, and the silver verification runs after silver
