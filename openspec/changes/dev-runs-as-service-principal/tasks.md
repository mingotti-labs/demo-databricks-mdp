## 1. Guard and runner

- [ ] 1.1 `cicd/block_bundle_deploy.py` (pure check plus stdin entry point, exit 2 with the steps to use) and `tests/cicd/test_block_bundle_deploy.py` (dev, no target, prd, patterns bundle by path and by working directory, validate, `jobs run-now`)
- [ ] 1.2 `PreToolUse` hook on `Bash|PowerShell` in `.claude/settings.json`; check in a session that `databricks bundle deploy -t dev` is refused and `databricks bundle validate -t dev` runs
- [ ] 1.3 `cicd/run_dev.py` and `tests/cicd/test_run_dev.py` (job name, parameters payload, job not found)

## 2. Move job

- [ ] 2.1 `migrations/move_dev_tables.py` (D4) and the `move_dev_tables` job in the `dev` target of `cicd/databricks/free.yml` and `standard.yml`; regenerate (`uv run python cicd/apply_edition.py`); `databricks bundle validate -t dev` and `-t prd` (no job in prd)
- [ ] 2.2 Push, open the implementation PR as a draft; wait for `deploy-dev`; confirm the SP's dev copies of `move_dev_tables` and the four units exist

## 3. Pilot: yahoo bronze (no other run in flight)

- [ ] 3.1 Record counts of the 8 tables (`references/poc/pipeline-ownership/baseline.sql`); the user deletes `[dev handsonessential] bronze--yahoo--dev` (`00bac0f4`); confirm the tables stay
- [ ] 3.2 Grant the SP `MANAGE` and `ALL PRIVILEGES` on the 8 tables (the user runs it if the classifier blocks it); run `move_dev_tables` by id with the SP pipeline `21a97027`
- [ ] 3.3 Start the SP pipeline by id; compare counts (raw unchanged, closed SCD2 versions unchanged); read owners from Unity Catalog; record in the poc README and design.md (D5); stop and report

## 4. The rest (after the pilot is agreed)

- [ ] 4.1 Same steps for bronze portfolio, wikipedia, sec, then silver portfolio, wikipedia, sec, yahoo (D3 order), one pipeline at a time; fallback D6 per source with explicit approval for each drop
- [ ] 4.2 `ALTER TABLE mdp_dev.bronze_yahoo.fetch_state OWNER TO <sp>`
- [ ] 4.3 The user deletes the four human jobs `[dev handsonessential] run--{portfolio,wikipedia,sec,yahoo}--dev`
- [ ] 4.4 `run_dev.py` portfolio, wikipedia, sec, yahoo with `verify=true`, one at a time; all succeed; every table of the four sources owned by the SP and on an SP pipeline

## 5. Docs and clean-up

- [ ] 5.1 CONTRIBUTING step 4 (D7); CLAUDE.md Guardrails entry and Operational notes (deleted pipelines keep their tables; current human copies that own dev tables)
- [ ] 5.2 Probes register: rows for the ownership probe (`references/poc/pipeline-ownership/`); poc README conclusion
- [ ] 5.3 With approval: drop the scratch tables `bronze_yahoo.zz_probe_{raw,scd1,mv}`, delete `s3_raw/zz_probe/` and `/Workspace/Shared/poc/pipeline-ownership`
- [ ] 5.4 Mark the PR ready for review
