## 1. Guard and runner

- [x] 1.1 `cicd/block_bundle_deploy.py` (pure check plus stdin entry point, exit 2 with the steps to use) and `tests/cicd/test_block_bundle_deploy.py` (dev, no target, prd, patterns bundle by path and by working directory, validate, `jobs run-now`)
- [x] 1.2 `PreToolUse` hook on `Bash|PowerShell` in `.claude/settings.json`; check in a session that `databricks bundle deploy -t dev` is refused and `databricks bundle validate -t dev` runs (also in the workspace folder's `.claude/settings.json`, outside the repo, since sessions start there; a first version also refused text that only mentioned the command, fixed to match a command only)
- [x] 1.3 `cicd/run_dev.py` and `tests/cicd/test_run_dev.py` (job name, parameters payload, job not found)

## 2. Dev deploy as the SP

- [x] 2.1 Move job `migrations/move_dev_tables.py` in the dev target (built, then removed after O8, task 3.2)
- [x] 2.2 Push, open the implementation PR as a draft; wait for `deploy-dev`; confirm the SP's dev copies of the four units exist

## 3. Pilot: yahoo bronze (no other run in flight)

- [x] 3.1 Record counts of the 8 tables (`references/poc/pipeline-ownership/baseline.sql`); the user deletes `[dev handsonessential] bronze--yahoo--dev` (`00bac0f4`); the tables stay
- [x] 3.2 Grant the SP `ALL PRIVILEGES, MANAGE` on the 8 tables; run `move_dev_tables` as the SP: refused for all 8 (O8, `User is not an owner of Pipeline '00bac0f4...'`); plan revised to drop and reload (user approved)
- [x] 3.3 Drop the 8 tables; start the SP pipeline `21a97027` by id; counts identical to 3.1; owner the SP

## 4. The rest (drop and reload, user approved)

- [x] 4.1 portfolio: drop 18 tables; `run_dev.py portfolio --param verify=true` succeeded; 18 tables owned by the SP
- [x] 4.2 wikipedia: drop 3 (the user ran them; the classifier blocked the agent); `run_dev.py wikipedia --param verify=true` succeeded
- [x] 4.3 sec: drop 6 (user); SP bronze pipeline, `verify--bronze` (source sec), silver pipeline, `verify--silver--landing` (source sec), by id, all succeeded; no download
- [x] 4.4 yahoo: drop 4 Landing (user); `ALTER TABLE mdp_dev.bronze_yahoo.fetch_state OWNER TO <sp>`; `run_dev.py yahoo --param verify=true` succeeded (incremental from the kept `fetch_state`: prices 1,035, no reloads)
- [ ] 4.5 The user deletes the remaining human dev pipelines (`silver--yahoo`, `bronze--portfolio`, `silver--portfolio`, `bronze--wikipedia`, `silver--wikipedia`, `bronze--sec`, `silver--sec`) and jobs (`run--{portfolio,wikipedia,sec,yahoo}--dev`); every table of the four sources owned by the SP and on an SP pipeline

## 5. Docs and clean-up

- [ ] 5.1 CONTRIBUTING step 4 (D7); CLAUDE.md Guardrails entry and Operational notes (deleted pipelines keep their tables; current human copies that own dev tables)
- [ ] 5.2 Probes register: rows for the ownership probe (`references/poc/pipeline-ownership/`); poc README conclusion
- [ ] 5.3 With approval: drop the scratch tables `bronze_yahoo.zz_probe_{raw,scd1,mv}`, delete `s3_raw/zz_probe/` and `/Workspace/Shared/poc/pipeline-ownership`
- [ ] 5.4 Mark the PR ready for review
