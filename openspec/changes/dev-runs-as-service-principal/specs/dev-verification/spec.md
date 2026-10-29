## Purpose

Dev runs of the main bundle execute as the CI/CD service principal, so dev data
is owned by the identity that runs prd and its permissions are tested before prd.

## ADDED Requirements

### Requirement: The agent does not deploy or run the main bundle locally

A Claude Code hook in the repo SHALL refuse a `databricks bundle deploy`,
`databricks bundle run` or `databricks bundle destroy` command for the main
bundle, whatever the target, and SHALL name the steps to use instead. Commands
for the patterns bundle (`references/patterns/`) and every other `databricks`
command SHALL pass.

#### Scenario: Local dev deploy refused
- **WHEN** the agent runs `databricks bundle deploy -t dev --profile DEFAULT` in the repo
- **THEN** the command does not run and the agent is told to deploy through the PR and run the SP's copy with `cicd/run_dev.py`

#### Scenario: Default target refused
- **WHEN** the agent runs `databricks bundle run run_yahoo --profile DEFAULT` with no target
- **THEN** the command does not run

#### Scenario: Patterns bundle allowed
- **WHEN** the agent runs `databricks bundle deploy -t dev` from `references/patterns/`
- **THEN** the command runs

#### Scenario: Other commands allowed
- **WHEN** the agent runs `databricks bundle validate -t dev` or `databricks jobs run-now <id>`
- **THEN** the command runs

### Requirement: A dev unit runs as the service principal

`cicd/run_dev.py <unit>` SHALL run the CI/CD service principal's dev copy of
the unit's job (`[dev svc_cicd_github] run--<unit>--dev`) by its job id, pass
each `--param key=value` as a job parameter, wait for the run to end, print its
result and page URL, and exit non-zero unless the run succeeded. It SHALL fail
with a clear message when no such job exists (the PR's dev deploy has not run).

#### Scenario: Run with a parameter
- **WHEN** `uv run python cicd/run_dev.py yahoo --profile DEFAULT --param reload_symbols=AAPL` runs after the PR's `deploy-dev`
- **THEN** the SP's `run--yahoo--dev` job runs with `reload_symbols=AAPL`, as the SP, and the script exits 0 when it succeeds

#### Scenario: Job not deployed
- **WHEN** the unit has no SP dev job
- **THEN** the script exits non-zero and says to open the PR so `deploy-dev` deploys it

### Requirement: Dev tables of the dividend story are owned by the service principal

Every dev table of wikipedia, portfolio, sec and yahoo (bronze, Bronze Publish,
Silver Landing and `bronze_yahoo.fetch_state`) SHALL be owned by the CI/CD
service principal and, except `fetch_state`, managed by its dev pipelines; each
source's bronze and Silver Landing checks SHALL pass when run as the SP. No
human dev pipeline or job of those sources SHALL remain. SEC and Yahoo raw
SHALL be rebuilt from the files already in their volumes, with the same rows as
before the reload.

#### Scenario: Ownership afterwards
- **WHEN** the tables of the four sources are listed in `mdp_dev`
- **THEN** every owner is the SP and every pipeline id is an SP dev pipeline

#### Scenario: Raw replayed from the volume
- **WHEN** the SP's Yahoo bronze pipeline rebuilds the dropped tables
- **THEN** each table's row count, file count and closed SCD2 version count equal the counts taken before the drop

#### Scenario: Units succeed as the SP
- **WHEN** `cicd/run_dev.py` runs portfolio, wikipedia and yahoo with `verify=true`, and SEC's two pipelines and two verify jobs run by id (no new download), one at a time
- **THEN** each run succeeds
