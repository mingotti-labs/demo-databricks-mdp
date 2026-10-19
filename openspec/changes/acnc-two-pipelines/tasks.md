## 1. Probes (dev, scratch pipelines, no acnc resource touched)

- [x] 1.1 P1: two scratch pipelines, an Auto CDC snapshot SCD2 target with closed versions in the source one; move it with the ALTER; verify closed versions unchanged, an unchanged rerun adds none, one changed key adds exactly one
- [x] 1.2 P2: ALTER a table while the source pipeline still defines it, run the source; record the outcome
- [x] 1.3 P3: delete the emptied source pipeline (user runs the delete); verify the moved table keeps its rows
- [x] 1.4 P4: in one pipeline, a two-part `name=` lands in the right catalog and schema, and a dataset reading it with `spark.read.table("<schema>.<t>")` resolves in-graph and runs after it
- [x] 1.5 P5: on the merged shape, a full refresh is refused and a normal update runs
- [x] 1.6 Record results in design.md; if any contradicts D1-D6, stop and update design/specs with the user before group 2; delete scratch pipelines (user)

## 2. PR-A: migration job

- [x] 2.1 Add `migrations/acnc_two_pipelines.py` (stop sources, idempotent ALTERs, report owner per table, then delete the two emptied source pipelines once every moved table reports its destination; design D4 amended) and `resources/jobs/migrate_acnc_two_pipelines.job.yml`; verify `bundle validate` and `ci/affected_units.py --base origin/main` reports no unit
- [x] 2.2 Open PR-A; after merge verify `main.yml` deployed it to tst/prd and ran no unit

## 3. Migration runs

- [x] 3.1 Per environment (dev, then tst, then prd): record row and closed-version counts of the three tables, run the migration job by id, verify each table's `pipelines.pipelineId` is its destination, the counts are unchanged and the two old pipelines are gone

## 4. PR-B: consolidation

- [x] 4.1 Bronze: ingestion pipeline includes `acnc_publish/**`, SCD datasets get qualified names, `reset.allowed=false` on scd2, display name `bronze--acnc--`; remove `acnc_charity_register_scd_modeling`; verify `bundle validate`
- [x] 4.2 Silver: normalised pipeline includes the landing file with a qualified name, display name `silver--acnc--`; remove `silver_landing_acnc`; verify `bundle validate`
- [x] 4.3 Jobs: delete `silver_acnc` and the migration job, display `verify_acnc_charity_register` as `verify--bronze--acnc`, flatten `run_acnc` (D5); verify `bundle validate` and `uv run python -m pytest` pass
- [ ] 4.4 Open PR-B; after its dev deploy run `run--acnc--dev` by job id; verify SUCCESS, closed-version count unchanged, removed pipelines gone, tables intact

## 5. Docs

- [x] 5.1 NAMING.md (one pipeline per layer, display names, removing a pipeline, `verify--<layer>--<source>`), CLAUDE.md acnc entry (layout, reset property and refused full refresh), `ci/affected_units.py` docstring example; verify by reading the diff

## 6. Post-merge verification

- [ ] 6.1 After PR-B merges, verify `deploy-tst` and (after approval) `deploy-prd` ran `run_acnc` with SUCCESS, the old pipelines are gone and the three tables keep their counts in each environment
