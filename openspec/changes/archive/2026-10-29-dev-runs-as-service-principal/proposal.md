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
- The 40 human-owned dividend-story dev tables are rebuilt under the SP: the
  user deletes the human pipelines and jobs, the tables are dropped (explicit
  approval), and the SP's pipelines rebuild them. SEC and Yahoo raw replay
  every file in their volumes, so their SCD2 history comes back too;
  Wikipedia's and portfolio's dev SCD2 history restarts.
  `bronze_yahoo.fetch_state`, a plain table, is handed over with `OWNER TO`.
  A move without a reload is not possible (probe O1-O8): the move checks the
  owner of the source pipeline, even deleted, and of the destination, and a
  pipeline's owner cannot change on Free Edition.
- Docs: CONTRIBUTING step 4 (open the implementation PR as a draft, let
  `deploy-dev` deploy as the SP, run its copy with `cicd/run_dev.py`); the rule
  moves into CLAUDE.md's Guardrails; the ownership notes list the current state.
- The ownership probe (`references/poc/pipeline-ownership/`) and its rows in the
  probes register.

## Capabilities

### New Capabilities
- `dev-verification`: dev runs of the main bundle go through the SP's dev
  copies (hook, `run_dev.py`), and the dividend story's dev tables are owned by
  the SP.

### Modified Capabilities
None. CI still deploys dev on every PR and runs no units there.

## Impact

- New: a `.claude/settings.json` hook
  entry (the guard lives in `cicd/block_bundle_deploy.py`), `cicd/run_dev.py`,
  tests under `tests/cicd/`; the same hook in the workspace folder's
  `.claude/settings.json`, outside the repo, where sessions start.
- Docs: `CONTRIBUTING.md`, `CLAUDE.md`, `references/docs/registers/probes.md`,
  `references/poc/pipeline-ownership/`.
- Dev only: 40 tables rebuilt under the SP. The user deletes the human dev
  pipelines and jobs of the four sources. prd is untouched.
- Workflow: implementation PRs open as drafts before the dev check.

## Cross-repo dependencies

None. The SP already holds `USE_SCHEMA`/`CREATE_TABLE` on every schema involved
and read/write on the source volumes (`demo-databricks-iac`).

## Model

Opus: the move was unproven and the plan changed mid-way (probe O8), as
expected.
