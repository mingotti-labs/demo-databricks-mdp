## Context

See proposal.md - Why. Current state that shapes the approach:

- `main.yml` has two jobs, `deploy-tst` and `deploy-prd` (the latter
  behind the `prd` GitHub Environment's required reviewer). Each checks out
  `main` and runs `databricks bundle deploy`. GitHub records each as a
  deployment for its environment with the commit SHA and a final status
  (`success` only when the whole job succeeded) - confirmed via
  `gh api repos/.../deployments?environment=prd`.
- `databricks bundle validate -o json` returns the resolved bundle: per
  pipeline, its `libraries` (globs/files as workspace paths under
  `${workspace.file_path}`) and `configuration` (e.g.
  `normalised_spec: src/layers/silver/normalised/specs/acnc.yml`); per job,
  its tasks, with `pipeline_task.pipeline_id` left unresolved as
  `${resources.pipelines.<key>.id}` - confirmed for `silver_acnc`.
- Pipeline code imports shared code through `sys.path`, not `libraries`,
  always as absolute imports rooted at `src/` (`from common.silver_landing
  import land`, `from layers.silver.normalised import transforms as sn`).
  `transforms.py` itself imports `common.normalised_spec`, so imports
  must be followed transitively.
- Free Edition runs one pipeline/job at a time.
- Existing orchestration: `silver_acnc`/`silver_airroi` jobs (landing →
  normalised → tag); bronze verify jobs per source;
  `verify_silver_normalised` takes a `source` job parameter.

## Goals / Non-Goals

**Goals:**
- Exact attribution: every file or config change maps to the resources
  that use it, derived from the bundle and the Python source, never from
  a hand-maintained list.
- Run nothing when nothing runnable is affected.
- Self-healing: a failed or skipped run is retried by the next deploy.
- A lookup that is thoroughly documented and unit-tested offline.

**Non-Goals:**
- Cross-unit data dependencies (a future gold domain reading acnc's
  silver tables is not re-run when acnc changes). When domains arrive,
  either their run job chains the units it reads (`run_job_task`, which
  the lookup already follows) or a later change adds lineage-based
  propagation.
- `run_<unit>` jobs for sources other than acnc/airroi (follow-up
  changes, Sonnet, pattern repeat).
- Running anything on PRs / `dev`.
- Detecting files read by hardcoded string paths not present in bundle
  config.

## Decisions

### D1. A unit is a `run_`-prefixed job; opt-out is a job tag
The run job is the unit: its key prefix identifies it, its task graph
defines what it covers, and `tags: {ci_auto_run: "false"}` excludes it.
Everything about a unit lives in one YAML file.
*Alternatives*: a separate unit list or path map (drifts, maintained by
hand); a tag as the identity (`ci_unit: acnc`) - works, but duplicates the
key and the `run_` prefix also reads clearly in the UI
(`run--acnc--tst`).

### D2. Config changes: diff the resolved bundle at base and head
Run `bundle validate -t <target> -o json` at head and at base (base
checked out into a temporary `git worktree`), then compare each pipeline
and job's resolved JSON. Any difference, or a resource new at head,
makes it affected. Resource YAML edits, `databricks.yml` variable changes
(`acnc_row_limit`), and changes to a run job itself are all caught the
same way, per target.
*Alternatives*: `bundle deploy` output (misses code-only changes, the
`phase4e` failure); `git diff` of `resources/*.yml` (misses variables,
and a YAML file is not one resource).

### D3. File changes: files each resource uses, plus their imports
For each resource, collect the repo files it uses:
- pipeline `libraries` (`file.path`, `notebook.path`, `glob.include`),
  matched against the repo's file list;
- job task `notebook_task.notebook_path` / `spark_python_task.python_file`
  (notebook paths have no `.py`; try both);
- any configuration, `base_parameters` or job parameter default whose
  value, relative to the bundle root, is an existing repo file.

Workspace paths are mapped back to repo paths by stripping the resolved
`workspace.file_path` prefix. Then follow imports: parse each used `.py`
with `ast`, resolve `import a.b` / `from a.b import c` against `src/`
(`src/a/b.py`, `src/a/b/__init__.py`, or `src/a/b/c.py` for a submodule
import), ignore anything not in `src/` (third-party), and repeat until no
new files appear. A resource is affected if any file in that closure is
in `git diff --name-only base head`.
*Alternatives*: declare shared modules in `libraries` (rejected: makes
them run as pipeline source, which broke `silver_landing_airroi` in
`phase4d`); treat all of `src/common` as "affects everything" (violates
"run nothing unless affected" and over-runs).

### D4. Reach: follow job tasks
A run job reaches: itself, each `pipeline_task` pipeline, and each
`run_job_task` job and, recursively, what that job reaches. The job keys
are parsed from the unresolved `${resources.<type>.<key>.id}`
references. A unit is affected if anything it reaches is affected.

### D5. Base = last successful deployment of that environment
The script asks the GitHub Deployments API for the environment's
deployments, newest first, and takes the SHA of the first one whose
latest status is `success`. The current run's own deployment is still
`in_progress`, so it is never picked. If none exists, it reports no units
and says so.
*Alternative*: `HEAD~1` - simpler, but a rejected prd approval or a failed
run would drop that merge's units for good.

### D6. Unit job shape
`run_acnc`: `acnc_charity_register_ingestion` → `..._scd_modeling` →
`run_job_task verify_acnc_charity_register` → `run_job_task silver_acnc`
→ `run_job_task verify_silver_normalised` (`source: acnc`).
`run_airroi`: same shape with airroi's resources and
`verify_airroi_market_summary_pattern`, tagged `ci_auto_run: "false"`
(still useful as a one-button manual run). Existing jobs are reused, not
duplicated or removed. `verify_silver_landing` is cross-source and is not
part of any unit.

### D7. Code layout: `ci/affected_units.py`, pure core plus thin CLI
`ci/` is a new top-level folder: this is CI tooling, not deployed code,
so it stays out of `src/` (anything in `src/` is uploaded with the
bundle). The module has pure functions over the validate JSON, the repo
file list and the changed-file list (unit-tested in `tests/ci/` with
small inline fixtures, no network, no Databricks), and a `main()` that
does the I/O: `git`, `databricks bundle validate`, `gh api`. Standard
library only. Output: affected unit names on stdout, one per line; the
unattributed changed files and the base SHA on stderr and in
`$GITHUB_STEP_SUMMARY`.

Documentation is part of the deliverable: a module docstring that walks
through the whole algorithm with a worked example (the `phase4e`
shared-code commit), what counts as "used", what is deliberately not
detected, and how to add a unit; a docstring on every function stating
inputs, outputs and the rule it implements.

### D8. Workflow
In both deploy jobs, after `bundle deploy`: `actions/checkout` with
`fetch-depth: 0` (base commit and worktree), `GH_TOKEN` with
`deployments: read`, then:

```
units=$(python ci/affected_units.py --target tst --head "$GITHUB_SHA")
for u in $units; do databricks bundle run "run_$u" --target tst || failed=1; done
exit ${failed:-0}
```

A top-level `concurrency: {group: deploy, cancel-in-progress: false}`
serialises workflow runs. GitHub keeps one pending run per group and
cancels older pending ones; that is safe because the base is the last
*success*, so the surviving run covers the cancelled run's changes.

## Risks / Trade-offs

- [A file is used only via a hardcoded path in code] → not attributed;
  listed as unattributed in the step summary, visible on every deploy.
- [Validate at base fails, e.g. a base commit with a broken bundle] → the
  step fails loudly; fix forward or re-run. Not handled defensively.
- [Shared-code change triggers many units, lengthening `main.yml`] →
  only auto-run units count; today that is acnc alone.
- [`bundle run` on a job whose last task is a `run_job_task` reports the
  outer job's result] → confirmed during implementation in `dev` before
  relying on it in `tst`.
- [First deploy after this merges] → base is `2025e75`; `run_acnc` is new
  at head, so `tst` runs acnc. That is the intended first end-to-end
  check, not a surprise.

## Migration Plan

1. Implementation PR deploys `run_acnc`/`run_airroi` to `dev` as the SP
   (PR flow). Run `run_acnc` in `dev` by its SP-owned job ID to prove the
   chain; check the lookup against real history locally.
2. Merge: `deploy-tst` deploys and runs `run_acnc` (D8, risk 5). Approve
   prd: same.
3. Rollback: revert the workflow step; the run jobs are harmless on their
   own.
