## 1. Rename ci to cicd
- [x] 1.1 `git mv ci cicd`, `git mv tests/ci tests/cicd`; update `pyproject.toml` `testpaths` and any path inside the script/tests; run `uv run pytest`

## 2. Edition folders
- [x] 2.1 Move `databricks.yml` to `cicd/databricks/standard.yml` and `.github/workflows/*.yml` to `cicd/workflows/standard/` unchanged; point `ci/` references at `cicd/`
- [x] 2.2 Create `cicd/databricks/free.yml` (no `tst` target) and `cicd/workflows/free/` (`pr.yml` same; `main.yml` without `deploy-tst`, `deploy-prd` no longer needs it, base for affected units still the last successful `prd` deployment)
- [x] 2.3 Add `config.json` with `edition: free`, `environments: [dev, prd]`

## 3. Apply script
- [x] 3.1 Write `cicd/apply_edition.py` (copy + `--check`, header comment in generated files) with unit tests under `tests/cicd/`, including the check that bundle targets equal `environments`
- [x] 3.2 Run it for `free`; regenerate root `databricks.yml` and `.github/workflows/`; run for `standard` in a scratch copy and confirm the output equals today's files apart from the header comment

## 4. CI and docs
- [x] 4.1 Add the drift check to `pr.yml` (both editions); update path filters (`cicd/**`, `config.json`)
- [x] 4.2 CONTRIBUTING.md: generated-files note; CLAUDE.md and NAMING.md: `cicd/` paths and the free-edition targets

## 5. Verify
- [x] 5.1 `databricks bundle validate -t dev` and `-t prd` with the generated root file; `-t tst` reports an unknown target
- [ ] 5.2 Open the implementation PR; confirm PR checks (validate, drift check, tests) pass and dev deploys
