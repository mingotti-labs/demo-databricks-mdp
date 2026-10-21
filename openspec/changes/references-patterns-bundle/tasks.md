## 1. Patterns bundle
- [ ] 1.1 Create `references/patterns/databricks.yml` (bundle `demo-databricks-mdp-patterns`, `catalog` variable, `include: resources/**/*.yml`, `dev` target only, same host as the main bundle)
- [ ] 1.2 `git mv` the seven variant resource files to `references/patterns/resources/pipelines/` and their `src/layers/bronze/clickstream/<variant>/` folders to `references/patterns/src/<variant>/`; fix each `libraries` glob; change the display name segment `template` to `pattern`
- [ ] 1.3 `databricks bundle validate -t dev` from `references/patterns/`

## 2. Main bundle
- [ ] 2.1 Add `sync: exclude: ["references/**"]` to `cicd/databricks/{standard,free}.yml`; regenerate with `apply_edition.py`; `apply_edition.py --check` and `bundle validate -t dev|prd` from the root show the seven pipelines gone

## 3. Docs
- [ ] 3.1 Update NAMING.md and CLAUDE.md (`template` to `pattern`, the structure tree, the clickstream variants note) and the register's "Code" paths for the seven variants

## 4. Cleanup before merge (each deletion needs explicit approval)
- [ ] 4.1 Confirm the seven pipelines own no tables in dev and prd, then delete them in dev and prd (they are SP-owned; see NAMING.md "Removing a pipeline")

## 5. Verify
- [ ] 5.1 Deploy the patterns bundle to `dev` by hand and confirm seven pipelines exist; open the PR and confirm its checks pass, including the dev deploy with no deletion prompt
