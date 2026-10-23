## 1. Inventory and probe
- [x] 1.1 airroi inventory (design.md)
- [x] 1.2 Inventory clickstream and neon (pipelines, ids, table owners) in dev and prd
- [x] 1.3 P1: change feed from an Auto CDC SCD1 target feeds a Landing streaming table

## 2. neon (dev only)
- [x] 2.1 Dev ownership fix: user deleted the human pipelines and jobs, the 16 stale dev tables were dropped with approval (2026-10-23)
- [x] 2.2 Change data feed on the SCD tables; four Landing streaming tables (`land_changes`, `scd2` flag); silver displayed `silver--neon--<target>`; reset task
- [x] 2.3 `run_neon` (`ci_auto_run: "false"`) with `tag_patterns` and the `verify` gate (neon bronze verification is the generic `verify_bronze` job with `bronze_checks/neon.yml`; the Neon-source checks stay as manual notebooks); mapping entries
- [x] 2.4 Verify dev; checkpoint (2026-10-23): Landing x4 are streaming tables, equal to their bronze tables (200, 50, 500, 1,240), one stamp each; the second load wrote 0 rows to bronze and Landing; `verify=true` run passes
- [x] 2.5 neon resources defined under `targets.dev.resources` (dev only); user deletes the prd copies before the prd deploy

## 3. clickstream
- [ ] 3.1 Dev ownership fix as 2.1
- [x] 3.2 Merge the Auto Loader and Python SCD pipelines (no migration job: SCD1 of append-only events is recreated from raw); Landing streaming table; silver displayed `silver--clickstream--<target>`
- [x] 3.3 `run_clickstream` (`generate` and `verify` parameters, `ci_auto_run: "false"`), mapping entries
- [ ] 3.4 Verify dev; checkpoint

## 4. airroi
- [ ] 4.1 Migration job (table moves, delete emptied pipelines); user approves deletes
- [ ] 4.2 Merge pipelines; bronze full pattern on both SCD2 tables; two Landing streaming tables; Normalised through the `normalised` task; remove `silver_airroi`; flat `run_airroi`; `bronze_checks/airroi.yml`
- [ ] 4.3 One dev run with `verify=true` (about $0.80); checkpoint. prd: migration only; a verified prd run only on request

## 5. Clean-up: reference-only code to the patterns bundle (last; can be cut)
- [ ] 5.1 Move `charity_register_scd1`, `unspsc_public_scd1`, `property_scd1`, neon `customers_scd1` and `products_scd1` to the patterns bundle; drop the live tables in dev and prd (explicit approval); bronze verification specs stop listing them
- [ ] 5.2 `charity_register_valid` stops stamping; remove the guard test exception
- [ ] 5.3 Move the SQL twins to the patterns bundle: neon SQL SCD pipeline and SQL SCD2 merge job, clickstream SQL SCD pipeline (and its human-owned or stale dev tables, with approval); empty the exempt lists in the specs
- [ ] 5.4 Merge the CKAN HTTP retry (branch `fix/ckan-http-retry`)

## 6. Specs and docs
- [ ] 6.1 Empty the "Sources pending refactor" lists (MODIFIED deltas with full requirement text); update NAMING.md, CLAUDE.md, the patterns register and source registers
- [ ] 6.2 Archive
