## ADDED Requirements

### Requirement: Landing checks are listed per source
The Silver Landing verification SHALL read the Landing tables to check for a
source from `verification/silver_landing_checks/<source>.yml`, one file per
source listing each Landing table with its Bronze Publish table and whether it
is SCD2, and whether the source's Bronze Publish carries `ingested_timestamp`.
With the `source` parameter empty it SHALL check the tables of every file.
Adding a source SHALL need a new file and no change to the verification
notebook.

#### Scenario: One source
- **WHEN** the Landing verification runs with `source` `yahoo`
- **THEN** it checks the four tables listed in `yahoo.yml` and no others

#### Scenario: Every source
- **WHEN** the Landing verification runs with an empty `source`
- **THEN** it checks the tables of every file in the directory

#### Scenario: A source with no file
- **WHEN** the Landing verification runs with a `source` that has no file
- **THEN** it fails, naming the source

#### Scenario: A source forgotten
- **WHEN** a source has a `silver_landing` schema entry in
  `src/common/design_patterns.yml` and no check file
- **THEN** the unit tests fail
