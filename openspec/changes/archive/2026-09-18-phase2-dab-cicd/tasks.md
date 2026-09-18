## 1. Bundle skeleton

- [x] 1.1 Create `databricks.yml` at repo root with bundle name and `dev`/`tst`/`prd` targets, each pointing at the single workspace host and setting default catalog `mdp_dev`/`mdp_tst`/`mdp_prd` — `databricks bundle validate --target {dev,tst,prd} --profile DEFAULT` all pass with no errors or warnings. Also fixed two issues the CLI itself flagged: `tst`/`prd` (production mode) need an explicit `workspace.root_path` (not the default user-derived one, since CI — not my personal user — deploys those targets) set to `/Workspace/Shared/.bundle/${bundle.name}/${bundle.target}`, and an explicit `CAN_MANAGE` permission for `group_name: users` to acknowledge that shared path deliberately (solo workspace, so no real exposure, but made explicit rather than left as a warning)
- [x] 1.2 Confirm no account-level bundle resources are referenced — no resources defined yet; `databricks.yml` itself references no account-level resource type
- [x] 1.3 Create `resources/{jobs,pipelines,dashboards,apps}/` directories (placeholder `.gitkeep` files) and set `databricks.yml`'s `include:` to a pattern that reaches them (e.g. `resources/**/*.yml`) — verified with a throwaway `resources/jobs/throwaway.job.yml`, confirmed present via `bundle validate --output json`, then removed
- [x] 1.4 Create `src/layers/bronze/{neon,atlas}/`, `src/layers/silver/`, `src/layers/gold/{analytics_gateway,integration_gateway,ai_gateway}/`, and `src/common/` directories (placeholder `.gitkeep` files) — tree matches design.md's Repository structure decision
- [x] 1.5 Create `tests/common/` and a minimal `pyproject.toml`/pytest config so `uv run pytest` succeeds — `uv init` + `uv add --dev pytest`, `[tool.pytest.ini_options] testpaths = ["tests/common"]`. Zero real tests would exit 5 ("no tests collected", pytest's hardcoded behavior, no ini-level override exists), so added a trivial `tests/common/test_placeholder.py` — `uv run pytest` exits 0. Did not create a `tests/layers/` tree (see design.md)

## 2. CI authentication

- [x] 2.1 Attempt to create a Free Edition workspace service principal with an OAuth client secret via `databricks service-principals create` / workspace UI — superseded by a cleaner path: provisioned via Terraform instead of UI/CLI, as its own `demo-databricks-iac` change (`phase1-identity-governance`, archived 2026-09-18). Service principal `svc-cicd-github` created with an OAuth client secret; workspace-level SP creation confirmed available on Free Edition
- [x] 2.2 PAT fallback — not needed; OAuth M2M via the Terraform-managed service principal worked directly
- [x] 2.3 Store the chosen credential plus `DATABRICKS_HOST` as GitHub Actions repository secrets — done via `gh secret set` (values piped through command substitution from `terraform output`, never printed); `gh secret list` confirms `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`, `DATABRICKS_HOST` all present (masked), no value committed anywhere

Also added, to have something real to validate the pipeline against: `resources/jobs/hello_world.job.yml` + `resources/jobs/hello_world.py`, a minimal serverless notebook job that confirms its target's catalog. Deploying it with the SP surfaced two more real, evidence-based gaps beyond bundle-deploy access, both fixed in `phase1-identity-governance`: the SP needed the `workspace_access` entitlement (deploy-time), and `USE_CATALOG` on each catalog (run-time — a deployed job running `USE CATALOG` failed with a specific `PERMISSION_DENIED` until granted). `bundle run hello_world` now succeeds (`TERMINATED SUCCESS`) against `dev`, `tst`, and `prd`.

## 3. GitHub Environments

- [x] 3.1 Create GitHub Environments `dev`, `tst`, `prd` in repo settings — created via `gh api --method PUT repos/.../environments/<name>`; confirmed all three listed
- [x] 3.2 Add a required-reviewer protection rule to the `prd` environment only — added via the environments API (`reviewers[][type]=User`, `id` = repo owner); confirmed `dev`/`tst` have `protection_rules: []` and `prd` has `["required_reviewers"]`

## 4. PR workflow

- [x] 4.1 Add `.github/workflows/pr.yml` triggered on `pull_request` that runs `databricks bundle validate --target dev` — verified on a real PR (mingotti-labs/demo-databricks-mdp#8): first run failed (`databricks/setup-cli@v0.9.0` doesn't exist — the docs I checked were stale; actual tags go up to v1.17.0), fixed to `@v1.17.0` and pushed, re-ran automatically and passed. Genuine fail-then-pass, not staged
- [x] 4.2 Extend `pr.yml` to run `databricks bundle deploy --target dev` after validation succeeds, using the `dev` environment's secrets — verified on the same PR: `deploy-dev` job passed after `validate`

## 5. Main-branch workflow

- [x] 5.1 Add `.github/workflows/main.yml` triggered on push to `main` that runs `databricks bundle deploy --target tst` using the `tst` environment — verified on two real merges to `main` (#8, #9): `deploy-tst` ran automatically and succeeded both times
- [x] 5.2 Add a subsequent job in `main.yml` that runs `databricks bundle deploy --target prd` using the `prd` environment, depending on the tst job — verified: `deploy-prd` showed `status: waiting` (confirmed via the Actions API, `steps: []` — nothing executes pre-approval) both times, only starting after approval
- [x] 5.3 Approve the pending prd deployment on a test merge — done, twice (once per real merge, #8 and #9); both `deploy-prd` runs completed successfully afterward. Also added, per review feedback on the first approval: a `Summarize tst deployment` step (`databricks bundle summary --target tst` + a log link, written to `$GITHUB_STEP_SUMMARY`) so the required reviewer has something concrete to check before approving prd, not a bare prompt — shipped and verified working on the second merge (#9)
- [ ] 5.4 Reject a pending prd deployment on a second test merge — deferred; not worth a throwaway merge just to test rejection. `required_reviewers` rejection is standard, well-documented GitHub Environments behavior, not something specific to this workflow's YAML

## 6. Verification

- [x] 6.1 Confirm end-to-end: open a PR, see validate + dev-deploy run automatically; merge it, see tst deploy automatically and prd deploy wait for approval — walked through twice for real (PR #8, then PR #9 for the summary fix): both times `validate` + `deploy-dev` ran on the PR, merging triggered `deploy-tst` automatically, and `deploy-prd` waited for and then completed after manual approval
- [x] 6.2 Confirm no plaintext credential appears in `databricks.yml`, any workflow YAML, or git history — `git log --all -p -- databricks.yml .github/workflows` reviewed, no plaintext client secret, token, or `dapi...` PAT pattern found; only `${{ secrets.* }}` references
