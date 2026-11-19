## 1. Probes

- [ ] 1.1 Re-read the table quota; agree a clean-up with the user if a run would pass 488
- [ ] 1.2 P5: Python snapshot source with TIMESTAMP versions (fallback: epoch numbers)
- [ ] 1.3 P6: a pipeline file imports `scd2_migration.py` (fallback: `sys.path` insert)
- [ ] 1.4 P7: `spark.sql` inside the snapshot function
- [ ] 1.5 Record P5 to P7 in `references/poc/scd2-history-migration-python/` and `probes.md`

## 2. Baseline (plain)

- [ ] 2.1 `scd2_migration.py`: `history`, `live`, `versions`, `cutover`, `next_version`,
      `snapshot`, `migrate_and_load`, the column check, `technical_columns` (D1 to D3)
- [ ] 2.2 Notebook with `variant = plain`: steps 10 to 90, the SQL snapshot checks plus the
      technical-column check (D6)
- [ ] 2.3 Run in dev, then once more (pipeline reused); save the output; teardown

## 3. Key variants

- [ ] 3.1 `sid`: `legacy_key`, `row_hash`, the key rule (D4); notebook `variant = sid`; run in dev
- [ ] 3.2 P8, then one key per version (D4); notebook `variant = sid_unique`; run in dev
- [ ] 3.3 Teardown; quota back

## 4. Skill and docs

- [ ] 4.1 Skill `bronze-publish-scd2-autocdc-backfill-snapshot-python` (D8); its output runs
      as-is in a scratch pipeline and equals the notebook's table
- [ ] 4.2 README section, `design-patterns.md` entry, D7 stated in the module docstring
- [ ] 4.3 `openspec validate pattern-scd2-history-migration-python --strict`; patterns bundle
      `databricks bundle validate`
