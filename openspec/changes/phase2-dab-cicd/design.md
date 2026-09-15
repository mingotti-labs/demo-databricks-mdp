## Context

See proposal.md - Why. Relevant constraints from `CLAUDE.md`: Free Edition, serverless-only, single workspace, one metastore with environments separated by catalog (`mdp_dev`/`mdp_tst`/`mdp_prd`), no account-level API calls. Phase 1 (`demo-databricks-iac`) has already provisioned all three catalogs. This repo currently has no `databricks.yml` and no `.github/workflows/` — this change adds both from scratch.

## Goals / Non-Goals

**Goals:**
- One bundle, three targets, all resolving to the single Free Edition workspace
- A PR-to-dev feedback loop with no manual steps
- A merge-to-main path that reaches tst automatically and prd only after a human approves

**Non-Goals:**
- Wiring GitHub OIDC to an AWS IAM role — this repo's workflows only call the Databricks CLI/API, not AWS APIs directly, so there is no cloud credential to federate yet. Revisit this if a future phase adds a workflow step that calls AWS directly (e.g., an S3-side action outside Databricks).
- Any account-level Databricks Terraform or API usage — out of scope for Free Edition, and not needed since environments are catalogs, not workspaces.
- Notebook/pipeline/job resource definitions themselves — this change only builds the skeleton bundle and its deploy pipeline; concrete resources arrive with each Phase 3+ change.

## Decisions

**Databricks CLI auth for CI: OAuth machine-to-machine (service principal), not a PAT.**
Free Edition supports creating a workspace-level service principal and OAuth client secret. M2M OAuth secrets are scoped to the service principal, rotate independently of any human account, and don't expire on the same cadence as a user PAT tied to a personal login. A PAT remains the documented fallback in tasks.md in case Free Edition's SP support has gaps at implementation time, but the SP path is tried first.
Alternative considered: a personal PAT stored as a secret — simpler to set up but ties CI to one person's account and workspace permissions, which is worse for a repo meant to be a portfolio artifact showing sound practice.

**Environment gating via native GitHub Environments, not a separate approval action.**
GitHub Environments' built-in "required reviewers" protection rule pauses a job until approved, with no extra third-party action or token needed. Three environments (`dev`, `tst`, `prd`) map directly to the three bundle targets; only `prd` gets the required-reviewer rule.
Alternative considered: a manual `workflow_dispatch` step for prd — rejected because it loses the automatic "merge to main → tst passes → prd awaits approval" flow the roadmap calls for, requiring someone to remember to trigger it.

**Single combined workflow file per trigger, not one file per target.**
One `pr.yml` (validate + deploy dev) and one `main.yml` (deploy tst, then prd gated) keep the trigger-to-target mapping obvious at a glance, rather than spreading it across many small files a reader has to cross-reference.

**No AWS OIDC wiring in this change.**
See Non-Goals. Recorded as a decision (not silently dropped) because the original roadmap phrasing mentions OIDC-to-IAM; the proposal explicitly narrows that to "only when a workflow calls a cloud API," which none does yet.

**Repository structure: `resources/` by resource type, `src/` split into `layers/` and `common/`.**

```
demo-databricks-mdp/
  databricks.yml
  resources/
    jobs/
    pipelines/
    dashboards/
    apps/
  src/
    layers/
      bronze/
        neon/
        atlas/
      silver/
        <domain>/        # domains TBD, per Phase 4
      gold/
        analytics_gateway/
        integration_gateway/
        ai_gateway/
    common/               # shared importable Python modules (wheel packages, utilities)
  tests/
    common/               # mirrors src/common/ only
```

- `resources/<type>/` (not one flat directory): grouping `*.job.yml` / `*.pipeline.yml` / `*.dashboard.yml` / `*.app.yml` by kind keeps the directory navigable once Phase 3+ adds resources for five ingestion patterns plus ML, GenAI, and Apps. Requires `databricks.yml`'s `include:` to change from `resources/*.yml` to a recursive pattern (`resources/**/*.yml`) — verified in tasks.md rather than assumed, since the reference docs only show the flat form.
- `src/layers/{bronze,silver,gold}/<source-or-domain-or-gateway>/` mirrors the `catalog.schema` naming already fixed in `CLAUDE.md` (`bronze_<source>`, `silver_<domain>`, `gold_*_gateway`) rather than organizing by ingestion pattern or use case. Folder path tracking catalog path is a legibility win, especially for the portfolio-polish goal in roadmap Phase 11.
- `src/common/` holds shared, plainly importable Python (wheel packages, utility modules) — the part of `src/` that behaves like a normal Python package and is unit-testable the ordinary way.
- `tests/` mirrors `src/common/` only, 1:1, per the standard `databricks bundle init` jobs scaffold (`src/my_module/` → `tests/test_main.py`, run with `pytest`). It does **not** mirror `src/layers/`: the official `databricks pipelines init` scaffold has no `tests/` for transformation code — pipeline correctness is validated with inline data-quality expectations (`EXPECT` / `@dp.expect`) and `bundle run --refresh <table>`, not offline pytest. Revisit only if transformation logic is deliberately factored into plain functions that `src/layers/` code calls (a Phase 4 question, not this change's).

Trade-off accepted: this organizes by resource-type and data-layer instead of the roadmap Appendix C's original "one self-contained folder per OpenSpec change/use case." A single Phase 3 ingestion-pattern change now touches two places (one `resources/pipelines/*.yml` file, one `src/layers/bronze/<source>/` folder) instead of one unified folder. Judged worth it for the catalog-mirroring legibility gain; revisit if it proves awkward once Phase 3 actually lands.

**Resource type ownership: this repo vs. Terraform, not "scaffold every DAB resource type."**
The DAB resource schema (`databricks bundle schema`, CLI v1.16.1) defines 35 resource types. Rather than pre-create a `resources/<type>/` folder for all of them, this change scaffolds only the four types Phase 2 itself needs (`jobs`, `pipelines`, `dashboards`, `apps` — see tasks.md 1.3) and records the full ownership split as a reference in `CLAUDE.md`, so later phases know where a new resource type belongs without re-litigating it:
- Terraform (`demo-databricks-iac`) owns Unity Catalog governance and source-DB infra types (`catalogs`, `schemas`, `external_locations`, `secret_scopes`, `secrets`, `volumes`, and the Lakebase infra types if adopted).
- Not applicable: `clusters`, `cluster_policies`, `instance_pools` (Free Edition is serverless-only).
- This repo owns the remaining 17 workload types (`alerts`, `experiments`, `genie_spaces`, `model_serving_endpoints`, `models`, `registered_models`, `quality_monitors`, `vector_search_endpoints`, `vector_search_indexes`, `sql_warehouses`, `job_runs`, `postgres_synced_tables`, `synced_database_tables`, plus the four scaffolded now) — each gets its `resources/<type>/` folder created by the phase that first adds a resource of that type, not by this change.
Alternative considered: scaffold all 17 workload-type folders now for a complete reference structure — rejected as pre-building for phases 5-9 requirements that don't exist yet, against this project's own no-overengineering convention.

## Risks / Trade-offs

- [Free Edition may not support creating a service-principal OAuth client through the CLI/UI at implementation time] → Mitigation: tasks.md includes a verification step early, with PAT-in-secret as the documented fallback if SP creation is unavailable.
- [A required-reviewer rule on the `prd` GitHub Environment means only repo collaborators with write access can approve; for a solo project this is the account owner] → Mitigation: acceptable for a personal demo platform; call this out in the repo README per the roadmap's Phase 11 polish pass.
- [`bundle deploy` to `tst` and `prd` both run unattended once the bundle itself resolves cleanly — a bad `main` merge reaches tst before anyone reviews it] → Mitigation: PR-time `bundle validate` and PR-time dev deploy are the review gate; tst is intentionally cheap to redeploy, and prd carries the approval gate.

## Migration Plan

Net-new: no existing deployed resources to migrate. Rollout is: land `databricks.yml` and workflows on a branch, open a PR (exercises validate + dev deploy), merge (exercises tst deploy + prd approval gate) once tasks.md verification steps pass. Rollback is reverting the merge commit; no bundle resources are deployed yet for this repo, so there is nothing to tear down beyond what the bundle itself created.
