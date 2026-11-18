## 1. Probes

- [x] 1.1 Re-read the table quota (`databricks resource-quotas get-quota metastore ... table-quota`);
      if a run would pass the stop line, agree a clean-up with the user first
- [x] 1.2 P1: `AUTO CDC ONCE` from a batch temporary view in SQL (fallback: Python `once=True`)
- [x] 1.3 P2: snapshot flow next to the backfill: refused (one flow per snapshot target); D4
      changed to one snapshot flow
- [x] 1.3b P2c: the one flow of D4 (temporary views in the snapshot query, `last_altered` as
      version, first-update result, update without refresh; fallbacks in D4)
- [ ] 1.4 P3: change feed streamed in SQL; an unchanged appended row opens no version
      (fallback in D5)
- [ ] 1.5 Record P1 to P3 in `references/poc/scd2-history-migration/` and
      `references/docs/registers/probes.md`; drop the probe tables and twins with approval

## 2. Snapshot notebook (`bronze_publish_scd2_autocdc_backfill_snapshot_sql.py`)

- [ ] 2.1 Widgets; steps 10, 15, 20, 25 (legacy table, base table, materialized view, seed, D8)
- [ ] 2.2 Steps 30, 40, 50: write the pipeline file (D2, D4)
- [ ] 2.3 Step 55: create or reuse the pipeline and run it (D1)
- [ ] 2.4 Steps 60, 70: change the base table, refresh the view, run again
- [ ] 2.5 Step 80 (D7) and step 90
- [ ] 2.6 Run it top to bottom in dev, then once more (pipeline reused); save the output in
      `references/poc/scd2-history-migration/`; run step 90 with approval

## 3. Stream notebook (`bronze_publish_scd2_autocdc_backfill_stream_sql.py`)

- [ ] 3.1 Widgets; steps 10, 15, 20, 25 (legacy table, append-only source with change feed, seed)
- [ ] 3.2 Steps 30, 40, 50: write the pipeline file (D2, D5)
- [ ] 3.3 Step 55: create or reuse the pipeline and run it
- [ ] 3.4 Steps 60, 70: append rows, run again
- [ ] 3.5 Step 80 (D7) and step 90
- [ ] 3.6 Run it top to bottom in dev, then once more; save the output; run step 90 with approval

## 4. Docs

- [ ] 4.1 `references/patterns/README.md`: both notebooks (steps, slots, removal), the
      `WITH VERSION` guide with its performance note, and the limits found by P1 and P2 (D6)
- [ ] 4.2 `design-patterns.md`: two entries
- [ ] 4.3 `tag_patterns` mapping for `asset_dim_migrated`

## 5. Verify

- [ ] 5.1 `openspec validate pattern-scd2-history-migration --strict`; patterns bundle
      `databricks bundle validate`; quota re-read shows the slots back
