## Why

Every dev run of the dividend story (wikipedia, portfolio, sec, yahoo) was made
from a local `bundle deploy -t dev` under the human account, although CLAUDE.md
and the agent's notes say the CI/CD service principal's dev copies hold the
durable dev data. Result: 40 dev tables are owned by `[dev handsonessential]`
pipelines, the SP's dev copies own nothing, and the SP's permissions are only
tested in prd. A written rule did not stop it; the right way was also the slow
way, and CONTRIBUTING step 4 ("deploy to `dev`") reads as the wrong one.

## What Changes

- A Claude Code `PreToolUse` hook in the repo's `.claude/settings.json` refuses
  `databricks bundle deploy|run|destroy` for the main bundle (any target; dev is
  the default target), with a message naming the right steps. The patterns
  bundle (`references/patterns/`), deployed by hand in dev, stays allowed.
- `cicd/run_dev.py <unit> [--param key=value ...]` finds the SP's dev copy of
  `run_<unit>` (`[dev svc_cicd_github] run--<unit>--dev`), runs it by job id
  with the given job parameters, waits and prints the result.
- A dev-only job `move_dev_tables` (`migrations/move_dev_tables.py`), deployed
  by CI so it runs as the SP, attaches listed tables to an SP pipeline with
  `ALTER STREAMING TABLE|MATERIALIZED VIEW ... SET
  TBLPROPERTIES('pipelines.pipelineId'=...)`.
- The 40 human-owned dividend-story dev tables move to the SP's pipelines
  without a reload: the user deletes the human pipeline (its tables stay), the
  human grants the SP rights on those tables, `move_dev_tables` moves them, the
  SP's pipeline runs. Yahoo bronze goes first and is the final probe (does the
  SP's move work, does the owner become the SP); then the rest. The fallback,
  per source, is dropping the tables and reloading (SEC and Yahoo raw replay
  from their volume files). `bronze_yahoo.fetch_state` is a plain table, handed
  over with `OWNER TO`.
- Docs: CONTRIBUTING step 4 (open the implementation PR as a draft, let
  `deploy-dev` deploy as the SP, run its copy with `cicd/run_dev.py`); the rule
  moves into CLAUDE.md's Guardrails; the ownership notes list the current state.
- The ownership probe (`references/poc/pipeline-ownership/`) and its rows in the
  probes register.

## Capabilities

### New Capabilities
- `dev-verification`: dev runs of the main bundle go through the SP's dev
  copies (hook, `run_dev.py`); human-owned dev tables move to the SP's pipelines
  without a reload (`move_dev_tables`); the dividend story's dev tables end up
  with the SP.

### Modified Capabilities
None. CI still deploys dev on every PR and runs no units there.

## Impact

- New: a `.claude/settings.json` hook
  entry (the guard lives in `cicd/block_bundle_deploy.py`), `cicd/run_dev.py`,
  `migrations/move_dev_tables.py` and its dev-only job in
  `cicd/databricks/free.yml` and `standard.yml` (regenerated `databricks.yml`),
  tests under `tests/cicd/`.
- Docs: `CONTRIBUTING.md`, `CLAUDE.md`, `references/docs/registers/probes.md`,
  `references/poc/pipeline-ownership/`.
- Dev only: 40 tables move to the SP's pipelines (or, on the fallback, are
  reloaded). The user deletes the human dev pipelines and jobs of the four
  sources. prd is untouched.
- Workflow: implementation PRs open as drafts before the dev check.

## Cross-repo dependencies

None. The SP already holds `USE_SCHEMA`/`CREATE_TABLE` on every schema involved
and read/write on the source volumes (`demo-databricks-iac`).

## Model

Opus: the last step of the move (run by the SP, owner after the move) is
still unproven and may change the plan mid-way.
