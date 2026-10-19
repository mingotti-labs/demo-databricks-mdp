## 1. Run jobs

- [ ] 1.1 Add `resources/jobs/run_acnc.job.yml` (`run--acnc--${bundle.target}`, D6 chain) and verify `databricks bundle validate -t dev` passes and shows the job
- [ ] 1.2 Add `resources/jobs/run_airroi.job.yml` (same shape, `tags: {ci_auto_run: "false"}`) and verify validate passes and the tag appears in the resolved JSON

## 2. Lookup core (pure, unit-tested)

- [ ] 2.1 Create `ci/affected_units.py` with the module docstring (algorithm, worked `phase4e` example, what is not detected, adding a unit); add `tests/ci` to pytest `testpaths`; verify `uv run pytest` still passes
- [ ] 2.2 Implement unit discovery (`run_` prefix, `ci_auto_run` tag) with docstrings; verify tests for the "unit discovered" and "paid source" scenarios pass
- [ ] 2.3 Implement config diff between two validate JSONs (changed and new resources); verify tests for the "variable change" and "new resource" scenarios pass
- [ ] 2.4 Implement used-file collection (libraries, notebook paths with/without `.py`, config/parameter values naming repo files, workspace-path stripping); verify tests for the "pipeline source" and "spec file" scenarios pass
- [ ] 2.5 Implement transitive `src/` import resolution with `ast`; verify tests cover `import a.b`, `from a import b` (submodule), `from a.b import c`, third-party ignored, and the "shared module" scenario through `transforms.py`
- [ ] 2.6 Implement reach through `pipeline_task`/`run_job_task` and the final unit selection; verify tests for "nested job", "docs-only" and "source without a run job" pass

## 3. Lookup I/O

- [ ] 3.1 Implement `main()`: base lookup via `gh api` deployments (D5), base `git worktree` + validate, changed files, stdout units, stderr/step-summary report; verify locally against `dev` on a throwaway local commit that only edits a comment in `src/common/normalised_spec.py` (base = the branch tip before it): reports `acnc` and not `airroi` (opted out), the `phase4e` case; then base = `main`, head = branch tip: reports `acnc` (`run_acnc` is new)
- [ ] 3.2 Verify locally that a docs-only commit range reports no units and `--base` omitted on a never-deployed environment name reports no units with a message

## 4. Workflow

- [ ] 4.1 Update `main.yml`: `concurrency`, `fetch-depth: 0`, `permissions: deployments: read`, run step in `deploy-tst` and `deploy-prd` (D8); verify `bundle validate` on the PR and the YAML passes `actionlint` (`uvx` or `docker`, whichever runs)
- [ ] 4.2 After the PR's dev deploy, run `run_acnc` in `dev` by its SP-owned job ID; verify it completes and that `bundle run`-style waiting reports the outer job's result (design risk 4)

## 5. Docs

- [ ] 5.1 CONTRIBUTING.md "Adding a unit"; NAMING.md `run--<unit>--<target>` and the `ci_auto_run` tag; CLAUDE.md repository structure (`ci/`, `tests/ci/`); verify by reading each diff

## 6. Post-merge verification

- [ ] 6.1 After merge, verify `deploy-tst` ran `run_acnc` and succeeded, and the step summary shows base `2025e75`; after prd approval, the same for `deploy-prd`
