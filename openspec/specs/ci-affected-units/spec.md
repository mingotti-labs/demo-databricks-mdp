# ci-affected-units Specification

## Purpose
Decides, from the bundle definition alone, which runnable units a change
between two commits affects, so CI runs exactly those units and nothing
else.

## Requirements

### Requirement: A runnable unit is a run job
A runnable unit SHALL be a bundle job whose resource key starts with
`run_`. The unit's name is the rest of the key (`run_acnc` → `acnc`). The
lookup SHALL NOT depend on whether a unit is a source or a domain.

#### Scenario: Unit discovered from the bundle
- **WHEN** the bundle defines jobs `run_acnc`, `run_airroi`, and
  `verify_silver_normalised`
- **THEN** the units are `acnc` and `airroi`, and
  `verify_silver_normalised` is not a unit

### Requirement: Units opt out of automatic runs by tag
A run job tagged `ci_auto_run: "false"` SHALL never be reported for an
automatic run, whatever changed.

#### Scenario: Paid source changed
- **WHEN** a change affects only resources reached by `run_airroi`, which is
  tagged `ci_auto_run: "false"`
- **THEN** no unit is reported

### Requirement: Config changes affect their resource
A resource SHALL be affected when its resolved bundle configuration for
the target differs between the base and head commits, including a change
that comes only from a bundle variable.

#### Scenario: Variable change
- **WHEN** only `acnc_row_limit` changes for `tst` in `databricks.yml`
- **THEN** `acnc_charity_register_ingestion` is affected for `tst`, and so
  `acnc` is reported for `tst`

#### Scenario: New resource
- **WHEN** a resource exists at head but not at base
- **THEN** it is affected

### Requirement: File changes affect the resources that use them
A resource SHALL be affected when a changed file is one it uses: a file
matched by a pipeline's `libraries`, a job task's notebook or Python file,
a repo file named by a configuration or parameter value, or any `src/`
Python module imported, directly or transitively, by one of those files.

#### Scenario: Pipeline source file changed
- **WHEN** `src/layers/bronze/acnc/charity_register_raw.py` changes
- **THEN** `acnc_charity_register_ingestion` is affected

#### Scenario: Shared module changed
- **WHEN** only `src/common/normalised_spec.py` changes
- **THEN** every Silver Normalised pipeline and every job running
  `tag.py` is affected, because their files import it directly or through
  `transforms.py`

#### Scenario: Spec file changed
- **WHEN** only `src/layers/silver/normalised/specs/acnc.yml` changes
- **THEN** `silver_normalised_acnc` is affected, because its configuration
  names that file

### Requirement: Affected units are those whose run job reaches an affected resource
A unit SHALL be reported when its run job reaches an affected resource,
directly or through `run_job_task` chains, or when the run job itself is
affected.

#### Scenario: Reached through a nested job
- **WHEN** `verify_silver_normalised` is affected and `run_acnc` reaches it
  through a `run_job_task`
- **THEN** `acnc` is reported

### Requirement: Unmatched changes run nothing
A change that affects no resource reached by an auto-run unit SHALL report
no units. The lookup SHALL list the changed files it could not attribute
to any resource, for visibility, without failing.

#### Scenario: Docs-only change
- **WHEN** only `README.md` and `openspec/` files change
- **THEN** no unit is reported

#### Scenario: Source without a run job
- **WHEN** only `src/layers/bronze/ungm/unspsc_public_raw.py` changes and
  no run job reaches `ungm_unspsc_ingestion`
- **THEN** no unit is reported
