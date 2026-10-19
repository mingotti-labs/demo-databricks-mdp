## Why

`main.yml` deploys the bundle to `tst`/`prd` but never runs anything, so
`tst`/`prd` data goes stale until someone triggers each pipeline by hand
(done manually for airroi and acnc throughout `phase4d`/`phase4e`). The
obvious signal, `bundle deploy`'s "changed resources" output, only reflects
resource config: in `phase4e`, a commit that changed only shared Python
(`normalised_spec.py`, `transforms.py`) deployed as "0 changed" yet
affected every Silver Normalised source.

This is CI/CD, not orchestration: after a deploy, run what the change
affects, and nothing else. A change that affects no runnable unit runs
nothing.

## What Changes

- **Runnable units**: a new bundle job per unit, `run_<unit>`, that runs
  that unit's whole chain in order (for a source: bronze ingestion → bronze
  SCD → bronze verify → silver landing/normalised/tag → silver verify). A
  unit is a source today and a silver/gold domain later; the mechanism
  does not care which. This change adds `run_acnc` and `run_airroi`
  (airroi opted out of auto-run: paid API). Other sources get their
  `run_<unit>` job in follow-up changes; until then, changes to them run
  nothing, by design.
- **Affected-unit lookup** (`ci/affected_units.py`, unit-tested): given a
  base and head commit, derives which units the change affects entirely
  from the bundle itself, with no hand-maintained map:
  - resources whose resolved config differs between base and head
    (`databricks bundle validate -o json` at each commit), covering
    resource YAML and `databricks.yml` variable changes;
  - resources whose referenced files changed: pipeline `libraries`,
    job notebook paths, configuration values naming repo files (e.g.
    `normalised_spec`), plus every `src/` module those Python files import,
    transitively (catching shared-code changes like `phase4e`'s);
  - then every `run_<unit>` job that reaches an affected resource,
    excluding jobs tagged `ci_auto_run: "false"`.
- **Workflow**: `main.yml`'s `deploy-tst`/`deploy-prd` jobs, after
  deploying, run each affected unit in sequence (`bundle run`), base =
  the commit of that environment's last successful deployment. A failed run
  fails the job, so the next deploy diffs from the last success and
  re-runs it. A workflow-level `concurrency` group stops two merges from
  running units at once (Free Edition: one run at a time).
- Docs: CONTRIBUTING.md "Adding a unit" (one job, one tag decision),
  NAMING.md (`run--<unit>--<target>`), CLAUDE.md (`ci/`, tests layout).

## Capabilities

### New Capabilities
- `ci-affected-units`: how a change maps to the units it affects, and which
  units CI may run automatically.

### Modified Capabilities
- `ci-cd-pipeline`: tst and prd deploys now run the affected units after
  deploying; deploys are serialised.

## Model

Opus to propose (new convention, genuine design trade-off); Sonnet to
implement (applies an agreed design: one script with tests, two jobs, one
workflow change).

## Impact

- New: `ci/affected_units.py`, `tests/ci/`, jobs `run_acnc`, `run_airroi`.
  `pytest` `testpaths` gains `tests/ci`.
- `main.yml`: run step per environment, `concurrency`, needs
  `fetch-depth: 0` and the GitHub token to read deployments.
- `tst`/`prd` runs now happen on merge for acnc, lengthening `main.yml`
  by that chain's runtime when acnc (or shared code it imports) changes.
- No change to existing resources, tables, or the `dev`/PR flow.
