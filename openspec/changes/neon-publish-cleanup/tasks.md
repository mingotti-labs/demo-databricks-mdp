## 1. Before changing anything

- [ ] 1.1 Read the live quota (456 expected) and `bronze_neon` row counts per
      table, for the comparison after
- [ ] 1.2 `grep -rn "neon_publish\|silver_landing/neon\|neon__"` outside archived
      changes: every hit is in the removal list or is updated

## 2. Patterns bundle

- [ ] 2.1 `references/patterns/src/bronze_publish/bronze_publish_scd2_autocdc_snapshot_python.py`
      and its pipeline resource, from Neon's `customers_scd2.py`, reading the dev
      UNGM codes; `databricks bundle validate` in `references/patterns/` passes
- [ ] 2.2 Register entry `bronze_publish_scd2_autocdc_snapshot_python` and the
      SCD1 snapshot entry point to the patterns bundle, with the three findings
      kept; `design_patterns.yml` and the register tests pass

## 3. Backup

- [ ] 3.1 `references/backups/neon/`: the removed source files, the two pipeline
      definitions and the `run_neon` Publish and Landing tasks as separate YAML
      files, the two checks files, and `RECOVERY.md`
- [ ] 3.2 Following `RECOVERY.md` on a scratch copy restores a validating bundle
      (`apply_edition.py --check` and `databricks bundle validate -t dev`)

## 4. Removal

- [ ] 4.1 Delete `src/layers/bronze/neon_publish/` and `src/layers/silver/landing/neon/`;
      remove the two pipelines and the Publish and Landing tasks of `run_neon`
      from `cicd/databricks/free.yml` and `standard.yml`;
      `uv run python cicd/apply_edition.py`
- [ ] 4.2 `verification/silver_landing_checks/neon.yml` deleted; the Publish and
      Landing parts of `verification/bronze_checks/neon.yml` removed;
      `design_patterns.yml` keeps only `bronze_neon` for neon
- [ ] 4.3 CLAUDE.md, `data-sources.md` (neon) and the register say neon is the
      bronze ingestion only; `uv run python -m pytest` passes;
      `databricks bundle validate` passes for dev and prd

## 5. Verify and clean up

- [ ] 5.1 Draft PR deploys to dev as the service principal; `run_neon` as the
      service principal ingests: `bronze_neon` counts equal task 1.1's
- [ ] 5.2 The user deletes pipelines `bronze--neon--scd--python--dev` and
      `silver--neon--dev` and the stale human-owned Neon copies
- [ ] 5.3 With the user's approval, drop `bronze_neon_publish.*` (4),
      `silver_landing.neon__*` (4), their twins and the two `event_log_*` tables,
      listed by name first
- [ ] 5.4 Read the quota: 438 expected; results in design.md

## 6. Archive

- [ ] 6.1 Archive the change after the merge
