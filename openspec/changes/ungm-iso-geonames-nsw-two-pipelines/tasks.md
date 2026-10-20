## 1. PR-A: generic migration job

- [x] 1.1 Add `migrations/two_pipelines.py` (D2) and `resources/jobs/migrate_four_sources_two_pipelines.job.yml` (one task per source, `depends_on` + `run_if: ALL_DONE`); verify `bundle validate` and `ci/affected_units.py --base origin/main` reports no unit
- [ ] 1.2 Open PR-A; after merge verify tst/prd deployed it and ran no unit

## 2. Migration runs

- [ ] 2.1 Per environment (dev, then tst, then prd): run the job by id; verify every task succeeded, each of the ten tables reports its ingestion pipeline as owner with counts unchanged (row and closed versions recounted after the deletes), and the four SCD pipelines are gone

## 3. PR-B: bronze

- [ ] 3.1 For each source: ingestion pipeline adds the `_publish` glob and displays `bronze--<source>--`; SCD tables get qualified `name`/`target`, SCD2 tables `pipelines.reset.allowed=false`; SCD pipeline resource removed; verify `bundle validate`

## 4. PR-B: silver, verification, jobs

- [ ] 4.1 Landing pipelines display `silver--<source>--`; verify `bundle validate`
- [ ] 4.2 ungm and nsw_spatial SCD checks compare SCD2 current rows; verify jobs display `verify--bronze--<source>--`
- [ ] 4.3 `verify_silver_landing` takes `catalog`/`source` job parameters and filters by source when given; verify `bundle validate`
- [ ] 4.4 Add `run_ungm`, `run_iso`, `run_geonames`, `run_nsw_spatial` (D5); remove the migration job and notebook; verify `bundle validate`, `uv run python -m pytest`, and the lookup selects the four units
- [ ] 4.5 Open PR-B; after its dev deploy run each `run--<source>--dev` by id, one at a time; verify SUCCESS and SCD2 closed-version counts unchanged

## 5. Docs and specs housekeeping

- [ ] 5.1 CLAUDE.md source entries (one pipeline per layer), data-sources register if it names pipelines; verify by reading the diff

## 6. Post-merge

- [ ] 6.1 After PR-B merges, verify tst and prd ran the four units with SUCCESS, the SCD pipelines are gone and SCD2 counts are unchanged in each environment
