## 1. Bundle skeleton

- [ ] 1.1 Create `databricks.yml` at repo root with bundle name and `dev`/`tst`/`prd` targets, each pointing at the single workspace host and setting default catalog `mdp_dev`/`mdp_tst`/`mdp_prd` — verify `databricks bundle validate --target dev` (and `tst`, `prd`) each resolve with no errors
- [ ] 1.2 Confirm no account-level bundle resources are referenced — verify by inspecting `databricks.yml` for any account-level resource type
- [ ] 1.3 Create `resources/{jobs,pipelines,dashboards,apps}/` directories (placeholder `.gitkeep` files) and set `databricks.yml`'s `include:` to a pattern that reaches them (e.g. `resources/**/*.yml`) — verify by adding one throwaway resource file under `resources/jobs/` and confirming `databricks bundle validate --target dev` picks it up, then remove the throwaway file
- [ ] 1.4 Create `src/layers/bronze/{neon,atlas}/`, `src/layers/silver/`, `src/layers/gold/{analytics_gateway,integration_gateway,ai_gateway}/`, and `src/common/` directories (placeholder `.gitkeep` files) — verify the tree matches design.md's Repository structure decision
- [ ] 1.5 Create `tests/common/` (placeholder `.gitkeep`) and a minimal `pyproject.toml`/pytest config so `uv run pytest` collects zero tests without error — verify with `uv run pytest`; do not create a `tests/layers/` tree (see design.md)

## 2. CI authentication

- [ ] 2.1 Attempt to create a Free Edition workspace service principal with an OAuth client secret via `databricks service-principals create` / workspace UI — verify a client ID and secret are issued
- [ ] 2.2 If service-principal OAuth is unavailable on Free Edition, fall back to a scoped PAT for a dedicated CI user — verify the PAT works with `databricks bundle validate` locally using `DATABRICKS_TOKEN`
- [ ] 2.3 Store the chosen credential (`DATABRICKS_CLIENT_ID`/`DATABRICKS_CLIENT_SECRET` or `DATABRICKS_TOKEN`) plus `DATABRICKS_HOST` as GitHub Actions repository secrets — verify secrets appear (masked) in repo Settings > Secrets and no value is present in any committed file

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
