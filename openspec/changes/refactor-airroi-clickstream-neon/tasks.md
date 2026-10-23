## 1. Inventory and probe
- [x] 1.1 airroi inventory (design.md)
- [x] 1.2 Inventory clickstream and neon (pipelines, ids, table owners) in dev and prd
- [x] 1.3 P1: change feed from an Auto CDC SCD1 target feeds a Landing streaming table

## 2. neon (dev only)
- [ ] 2.1 Dev ownership fix: user deletes human pipelines and jobs, stale dev tables dropped with approval
- [x] 2.2 Change data feed on the SCD tables; four Landing streaming tables (`land_changes`, `scd2` flag); silver displayed `silver--neon--<target>`; reset task
- [x] 2.3 `run_neon` (`ci_auto_run: "false"`) with `tag_patterns` and the `verify` gate (keeps the existing neon verification job: Neon connection, seed data, ingestion); mapping entries
- [ ] 2.4 Verify dev; checkpoint

## 3. clickstream
- [ ] 3.1 Dev ownership fix as 2.1
- [ ] 3.2 Migration job; merge the Auto Loader and Python SCD pipelines; Landing streaming table; silver displayed `silver--clickstream--<target>`
- [ ] 3.3 `run_clickstream` (events generation first), `verify` gate, `bronze_checks/clickstream.yml`, mapping entries; verify dev; checkpoint

## 4. airroi
- [ ] 4.1 Migration job (table moves, delete emptied pipelines); user approves deletes
- [ ] 4.2 Merge pipelines; bronze full pattern on both SCD2 tables; two Landing streaming tables; Normalised through the `normalised` task; remove `silver_airroi`; flat `run_airroi`; `bronze_checks/airroi.yml`
- [ ] 4.3 One dev run with `verify=true` (about $0.80); checkpoint. prd: migration only; a verified prd run only on request

## 5. SCD1 move (last; can be cut)
- [ ] 5.1 Move `charity_register_scd1`, `unspsc_public_scd1`, `property_scd1`, neon `customers_scd1` and `products_scd1` to the patterns bundle; drop the live tables in dev and prd (explicit approval); bronze verification specs stop listing them
- [ ] 5.2 `charity_register_valid` stops stamping; remove the guard test exception
- [ ] 5.3 Merge the CKAN HTTP retry (branch `fix/ckan-http-retry`)

## 6. Specs and docs
- [ ] 6.1 Empty the "Sources pending refactor" lists (MODIFIED deltas with full requirement text); update NAMING.md, CLAUDE.md, the patterns register and source registers
- [ ] 6.2 Archive
