## 1. Inventory (read-only)
- [ ] 1.1 Per source and env: pipelines, ids, table owners (`tables get`), human vs SP; record in design.md

## 2. airroi
- [ ] 2.1 Migration job (table moves, delete emptied pipelines); user approves deletes
- [ ] 2.2 Consolidate pipelines, flat `run_airroi` with `tag_patterns`, remove `silver_airroi`
- [ ] 2.3 Verify dev/tst/prd; checkpoint

## 3. clickstream
- [ ] 3.1 Dev ownership fix: user deletes human pipelines/jobs, stale dev tables dropped with approval
- [ ] 3.2 Migration job; merge Auto Loader + Python SCD pipeline; silver display name
- [ ] 3.3 `run_clickstream` (events generation first), mapping entries, verify dev; checkpoint

## 4. neon
- [ ] 4.1 Dev ownership fix as 3.1
- [ ] 4.2 Silver display name; `run_neon` with `tag_patterns`; mapping entries
- [ ] 4.3 Verify dev; checkpoint

## 5. Specs and docs
- [ ] 5.1 Empty the "Sources pending refactor" lists (MODIFIED deltas with full requirement text); update NAMING.md and CLAUDE.md; register source notes
