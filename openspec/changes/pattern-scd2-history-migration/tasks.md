## 1. Probe

- [ ] 1.1 Re-read the table quota (`databricks resource-quotas get-quota metastore ... table-quota`);
      if above 484, agree a clean-up with the user before any run
- [ ] 1.2 P1 (design.md): minimal pipeline with D3's two flows on three rows in dev; record
      the result in `references/poc/scd2-history-migration/` and `references/docs/registers/probes.md`;
      switch to the Python fallback if SQL refuses `AUTO CDC ONCE` from a batch view

## 2. Notebook

- [ ] 2.1 Widgets and steps 10, 15, 20, 25 (tables and seed data, D7)
- [ ] 2.2 Steps 30, 40, 50: write `transformations/dim_asset_migrated.sql` (D3)
- [ ] 2.3 Step 55: create or reuse the pipeline with the SDK and run it to completion (D1)
- [ ] 2.4 Steps 60, 70: seed new changes, run again
- [ ] 2.5 Step 80: the checks in D5
- [ ] 2.6 Step 90: teardown behind the `teardown` widget

## 3. Run in dev

- [ ] 3.1 `databricks bundle validate` and deploy of the patterns bundle (syncs the notebook)
- [ ] 3.2 Run the notebook top to bottom in dev; step 80 passes; save the output in
      `references/poc/scd2-history-migration/`
- [ ] 3.3 Run it a second time: the pipeline is reused, step 80 still passes
- [ ] 3.4 Run step 90 with approval; quota re-read shows the slots back

## 4. Docs

- [ ] 4.1 `design-patterns.md` entry, `references/patterns/README.md` section (steps, slots, removal)
- [ ] 4.2 `tag_patterns` mapping for `dim_asset_migrated`

## 5. Verify

- [ ] 5.1 `openspec validate pattern-scd2-history-migration --strict`, patterns bundle validate in the PR
