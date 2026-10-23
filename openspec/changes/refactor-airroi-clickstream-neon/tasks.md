## 1. Inventory and probe
- [x] 1.1 airroi inventory (design.md)
- [x] 1.2 Inventory clickstream and neon (pipelines, ids, table owners) in dev and prd
- [x] 1.3 P1: change feed from an Auto CDC SCD1 target feeds a Landing streaming table

## 2. neon (dev only)
- [x] 2.1 Dev ownership fix: user deleted the human pipelines and jobs, the 16 stale dev tables were dropped with approval (2026-10-23)
- [x] 2.2 Change data feed on the SCD tables; four Landing streaming tables (`land_changes`, `scd2` flag); silver displayed `silver--neon--<target>`; reset task
- [x] 2.3 `run_neon` (`ci_auto_run: "false"`) with `tag_patterns` and the `verify` gate (neon bronze verification is the generic `verify_bronze` job with `bronze_checks/neon.yml`; the Neon-source checks stay as manual notebooks); mapping entries
- [x] 2.4 Verify dev; checkpoint (2026-10-23): Landing x4 are streaming tables, equal to their bronze tables (200, 50, 500, 1,240), one stamp each; the second load wrote 0 rows to bronze and Landing; `verify=true` run passes
- [ ] 2.6 After the iac grant is applied: add the Neon seed-data and source-versus-bronze checks back to neon's automated verification, run as the service principal
- [x] 2.5 neon resources defined under `targets.dev.resources` (dev only); user deletes the prd copies before the prd deploy

## 3. clickstream
- [x] 3.1 Dev ownership fix as 2.1 (dropped the two dev tables, recreated by the new pipelines)
- [x] 3.2 Merge the Auto Loader and Python SCD pipelines (no migration job: SCD1 of append-only events is recreated from raw); Landing streaming table; silver displayed `silver--clickstream--<target>`
- [x] 3.3 `run_clickstream` (`generate` and `verify` parameters, `ci_auto_run: "false"`), mapping entries
- [x] 3.4 Verified dev 2026-10-23: run 1 with verify=true all tasks SUCCESS (SCD1 600, Landing 600, raw 600, one transformed_timestamp); run 2 SUCCESS, Landing still 600 with one stamp (0 rows written)

## 4. airroi
- [x] 4.1 No migration job: a new load, as for the other full-load sources. The `reset` task of `run_airroi` drops the old Landing views, both SCD2 tables and the seven Normalised views while Landing is still a materialized view (dev drops approved by the user); the user deletes the emptied pipelines first
- [x] 4.2 One bronze pipeline (`bronze--airroi--<target>`, SCD2 files joined), bronze full pattern on both SCD2 tables, two Landing streaming tables in `silver--airroi--<target>` (Landing only), Normalised through the `normalised` task, `silver_airroi` and the Normalised pipeline removed, flat `run_airroi`, `bronze_checks/airroi.yml` (new `nullable_keys` option: `_district` is NULL for three markets), the four old verify notebooks and `verify--bronze--airroi` removed, `src/layers/silver/normalised/pipeline.py` retired
- [ ] 4.3 One dev run with `verify=true` (about $0.80); checkpoint. prd: migration only; a verified prd run only on request

## 5. Clean-up: reference-only code to the patterns bundle (last; can be cut)
- [x] 5.1 One representative per pattern moved to `references/patterns/` (schema `pattern_bronze_publish`, tables named by the register ID): SCD1 snapshot (from `unspsc_public_scd1`), SCD1 materialized view SQL, SCD1 stream SQL, SCD2 MERGE SQL job; the duplicates (`charity_register_scd1`, `property_scd1`, neon `customers_scd1` and `products_scd1` and the other SQL twins, the products merge) are removed from the live bundle; `tag_patterns` tags both pattern schemas; verification specs and `design_patterns.yml` no longer list them
- [x] 5.2 `charity_register_valid` stops stamping; the guard test has no exception and covers airroi
- [ ] 5.3 After the user deletes the emptied pipelines and jobs and approves the drops: drop the live tables no longer built (dev and prd SCD1 of acnc, ungm, nsw_spatial; dev neon `customers_scd1`, `products_scd1`, the six SQL tables, clickstream `web_events_scd1_sql`); deploy and run the pattern pipelines in dev
- [ ] 5.4 Merge the CKAN HTTP retry (branch `fix/ckan-http-retry`)
