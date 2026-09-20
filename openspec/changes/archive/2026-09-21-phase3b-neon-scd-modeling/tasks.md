## 1. Python (initial attempt — streaming Auto CDC, wrong)

- [x] 1.1 Built 6 `create_auto_cdc_flow` (streaming) flows against
      `bronze_neon.*_raw` directly
- [x] 1.2 Deployed, ran successfully on initial load (all tables empty
      before, matched source row counts after — 200/50/500/1240)
- [x] 1.3 Updated one customer's email in Neon (throwaway verification
      notebook, deleted after use), re-ran `neon_ecommerce_ingestion`, then
      re-ran this pipeline — **failed**:
      `[DELTA_SOURCE_TABLE_IGNORE_CHANGES] ... streaming tables may only use
      an append-only stream source`. `bronze_neon.customers_raw` is
      upsert-maintained (Lakeflow Connect MERGEs changed rows in place),
      not append-only — streaming Auto CDC cannot read it
- [x] 1.4 Checked whether `skipChangeCommits` fixes this — confirmed via
      Databricks docs it silently drops the updated rows instead of
      surfacing them, which would make SCD tracking never actually track
      anything. Rejected

## 2. Python (corrected — snapshot-based Auto CDC)

- [x] 2.1 Replaced all 6 flows: `create_auto_cdc_from_snapshot_flow`
      against a `@dp.materialized_view()` batch snapshot of each source
      table (4 snapshot views + 6 SCD flow files)
- [x] 2.2 Deployed — validated for dev/tst/prd
- [x] 2.3 Ran against `dev` — `COMPLETED`, all 6 tables populated matching
      source row counts (200/50/500/1240 for SCD1; SCD2 customers/products
      likewise on initial load)
- [x] 2.4 Re-ran the same update-then-reingest-then-rerun sequence as 1.3 —
      this time `COMPLETED` successfully. Verified: `customers_scd1` shows
      one row with the new email (overwritten); `customers_scd2` shows two
      rows for that id — old email with `__END_AT` set to the change's
      timestamp, new email with `__END_AT` null. Real, empirical SCD1-vs-SCD2
      proof, not assumed from documentation

## 3. SQL SCD1 (plain passthrough, no CDC)

- [x] 3.1 Realized `bronze_neon.*_raw` already satisfies "latest value per
      key" by construction — rewrote the SCD1 SQL files from the original
      (also-broken, streaming `AUTO CDC INTO`) approach to plain
      `CREATE OR REFRESH MATERIALIZED VIEW ... AS SELECT * FROM
      bronze_neon.<table>_raw`
- [x] 3.2 Deployed and ran — all 4 tables match source row counts exactly
      (200/50/500/1240)

## 4. SQL SCD2 (hand-rolled two-phase MERGE, as a job)

- [x] 4.1 Confirmed via Databricks/Delta Lake documentation that the
      two-phase `MERGE` pattern (expire old version, insert new version) is
      the standard, well-established SQL-native SCD2 approach for a
      snapshot-based source — not invented for this project
- [x] 4.2 Built `customers_scd2_merge.py` and `products_scd2_merge.py`
      (Python notebooks, thin `spark.sql()` wrappers for catalog
      parameterization around the actual `MERGE` statements) and
      `neon_scd2_merge_sql.job.yml` wrapping both as independent tasks
- [x] 4.3 Deployed and ran — both tasks `SUCCESS`. First run: 200/50 rows,
      matching source, each with a single open version (`__END_AT` null) —
      expected, since Phase A had nothing pre-existing to expire yet
- [x] 4.4 Updated a *second* customer (id=2, not the one already tested in
      Python) to prove Phase A's expire-on-change logic specifically, not
      just Phase B's initial-insert path. Re-ran ingestion, re-ran the merge
      job — confirmed `customers_scd2_sql` now has two correctly-bounded
      rows for id=2 (old email closed with `__END_AT`, new email active)

## 5. Cleanup and documentation

- [x] 5.1 Deleted both throwaway verification notebooks from the workspace
      after use
- [x] 5.2 Documented the streaming-vs-snapshot Auto CDC distinction and the
      SQL SCD2-as-a-job pattern in CLAUDE.md's "Sources" section
- [x] 5.3 Updated NAMING.md's `<table>_scd1`/`<table>_scd2` entry with the
      job-vs-pipeline distinction for SCD2
