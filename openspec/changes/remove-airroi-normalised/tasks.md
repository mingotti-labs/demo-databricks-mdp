## 0. Backup

- [x] 0.1 Backup in `references/backups/airroi-normalised/` (spec, job, pattern entry,
      RECOVERY.md), done in the proposal PR

## 1. Remove

- [ ] 1.1 `run_airroi`: drop `normalised`, `tag`; `tag_patterns` depends on `silver`;
      `verify_silver` runs `verify_silver_landing`; remove the `silver_normalised_airroi.*`
      entries from `also_drop`
- [ ] 1.2 Remove `specs/airroi.yml`
- [ ] 1.3 Remove `silver_normalised_airroi` from `src/common/design_patterns.yml`

## 2. Docs

- [ ] 2.1 `data-sources.md` airroi block, `design-patterns.md` used-by lists, `silver.md`
      pending-refactor sentence, CLAUDE.md pointer to the backup

## 3. Verify

- [ ] 3.1 `uv run pytest`, `openspec validate`, bundle validate for both editions
- [ ] 3.2 Dev: run `run_airroi` as the SP copy with `verify=true`; the schema
      `silver_normalised_airroi` stays empty and Landing checks pass
