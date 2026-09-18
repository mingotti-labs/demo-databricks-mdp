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

- [ ] 3.1 Create GitHub Environments `dev`, `tst`, `prd` in repo settings — verify all three appear under Settings > Environments
- [ ] 3.2 Add a required-reviewer protection rule to the `prd` environment only — verify `dev` and `tst` have no protection rules and `prd` shows the required reviewer

## 4. PR workflow

- [ ] 4.1 Add `.github/workflows/pr.yml` triggered on `pull_request` that runs `databricks bundle validate --target dev` — verify the check appears on a test PR and fails when `databricks.yml` is intentionally broken, then passes when fixed
- [ ] 4.2 Extend `pr.yml` to run `databricks bundle deploy --target dev` after validation succeeds, using the `dev` environment's secrets — verify the workflow run shows a successful deploy step on a test PR

## 5. Main-branch workflow

- [ ] 5.1 Add `.github/workflows/main.yml` triggered on push to `main` that runs `databricks bundle deploy --target tst` using the `tst` environment — verify a merge to `main` triggers a successful tst deploy
- [ ] 5.2 Add a subsequent job in `main.yml` that runs `databricks bundle deploy --target prd` using the `prd` environment, depending on the tst job — verify the run pauses in "Waiting" state for approval before the prd job starts
- [ ] 5.3 Approve the pending prd deployment on a test merge — verify `databricks bundle deploy --target prd` runs only after approval and completes successfully
- [ ] 5.4 Reject a pending prd deployment on a second test merge — verify the prd job is skipped/cancelled and no prd deploy occurs

## 6. Verification

- [ ] 6.1 Confirm end-to-end: open a PR, see validate + dev-deploy run automatically; merge it, see tst deploy automatically and prd deploy wait for approval — verify by walking one real PR through the full cycle
- [ ] 6.2 Confirm no plaintext credential appears in `databricks.yml`, any workflow YAML, or git history — verify via `git log -p -- databricks.yml .github/workflows` review
