## Why

The platform has no deployable bundle yet — no `databricks.yml`, no environment targets, and no automated path from a pull request to a running dev deployment. Everything from Phase 3 onward (ingestion patterns, modeling, ML, GenAI) needs a bundle to deploy into, and a repeatable CI/CD path so each new component ships the same way instead of by hand.

## What Changes

- New `databricks.yml` Databricks Asset Bundle with `dev`, `tst`, `prd` targets — all pointing at the single Free Edition workspace, differentiated by Unity Catalog catalog (`mdp_dev` / `mdp_tst` / `mdp_prd`) per `CLAUDE.md`
- New GitHub Actions workflow: `bundle validate` runs on every pull request
- New GitHub Actions workflow: `bundle deploy` to the `dev` target runs on every pull request
- New GitHub Actions workflow: `bundle deploy` to `tst` runs on merge to `main`; `bundle deploy` to `prd` runs on merge to `main` behind a manual approval gate (GitHub Environments protection rule)
- Databricks authentication for CI: OAuth machine-to-machine (service principal) or a scoped PAT stored as a GitHub Actions secret, used by `bundle deploy` — no long-lived personal token
- No cloud (AWS) resources are created or touched by this change, so no GitHub OIDC-to-IAM-role wiring is needed yet; that pattern is deferred until a workflow in this repo actually calls a cloud API directly (tracked as a follow-up, not part of this change)

## Capabilities

### New Capabilities
- `dab-bundle`: the `databricks.yml` bundle definition and its `dev`/`tst`/`prd` targets
- `ci-cd-pipeline`: GitHub Actions workflows for bundle validation and gated deployment, and the CI authentication method they use

### Modified Capabilities
(none)

## Impact

- Adds `databricks.yml` at the repo root and `.github/workflows/` with validate/deploy workflow files
- Introduces a GitHub Actions secret (Databricks OAuth client secret or PAT) and GitHub Environments (`dev`, `tst`, `prd`) with a required-reviewer protection rule on `prd`
- No existing code, catalogs, or Terraform-managed infrastructure is modified — this change only adds the deployment mechanism
- Depends on Phase 1 infrastructure (catalogs `mdp_dev`/`mdp_tst`/`mdp_prd`) already being provisioned, which it is
