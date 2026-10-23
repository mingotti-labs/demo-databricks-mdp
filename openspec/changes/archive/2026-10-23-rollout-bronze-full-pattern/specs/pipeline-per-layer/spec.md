## MODIFIED Requirements

### Requirement: No wrapper jobs
A job whose only purpose is to chain a unit's pipelines and steps for its
`run_<unit>` job SHALL NOT exist; `run_<unit>` SHALL hold those tasks
itself. A verification job SHALL exist only when it checks something no
other job checks; a check shared by sources SHALL be one job taking the
source as a parameter. Verification jobs SHALL be displayed as
`verify--<layer>--<source>--<target>` (or `verify--<layer>--<check>--<target>`
for a shared one).

**Sources pending refactor** (each change that refactors a source removes
it from this list):
- airroi: wrapper job `silver_airroi` to remove.

#### Scenario: acnc jobs after migration
- **WHEN** the bundle is validated for any target
- **THEN** there is no `silver_acnc` job, acnc's own jobs are `run_acnc`
  and `run_acnc` verifies bronze and silver (when `verify` is true) through the
  shared `verify_bronze` and `verify_silver_normalised` jobs with `source: acnc`
