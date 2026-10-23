## Context

Evidence and the table of sources are in proposal.md. The pattern itself is
`correct-platform-timestamps` D7 to D9 (snapshot Auto CDC from a view without
the per-load columns, change-feed Landing, `ingested_timestamp = __START_AT`).

## Decisions

- **D1 Same pattern, minimal per-source change.** ungm and nsw_spatial change
  only by enabling change data feed on the SCD2 table. iso and geonames also
  drop the stamped `transformed_timestamp` and the untracked-column list; their
  snapshot view is the raw table without `ingested_timestamp`
  (`subdivision_codes` from the deduped view, no stamp). Raw tables are not
  touched: `ingested_timestamp` stays where it is, and ungm and nsw_spatial need
  none.
- **D2 Landing: one shared shape.** Each Landing file becomes the acnc Landing
  (temporary view over the change feed with `land()`, then `create_auto_cdc_flow`
  keyed by the natural key plus `scd_valid_from_timestamp`), with
  `ingested_timestamp = __START_AT`. If the repeated code is more than a few
  lines per file, move it into `src/common/silver_landing.py` as one function.
- **D3 One reset notebook**, `migrations/reset_full_load.py`, parameters
  `catalog` and `drop` (a list of schema.table). It acts only while the first
  Landing table is still a materialized view, so it is a no-op once applied
  (acnc's own reset stays as it is). iso and geonames list their SCD2 tables as
  well as Landing; ungm and nsw_spatial list Landing only.
- **D4 Verification driven by a spec file.** `verification/bronze_checks/<source>.yml`
  lists, per table: raw table, key columns, SCD2 table, optional SCD1 table,
  optional quarantine table, expected raw columns. One notebook (`source`
  parameter) checks that raw has rows and the expected columns, that current SCD2
  rows equal the distinct non-null keys in raw (and equal SCD1 where listed),
  that raw equals those plus quarantine where a quarantine table is listed, and
  that raw keys are unique where no quarantine is listed. This is what the ten
  per-source notebooks check today, with one formula instead of five. One job
  `verify--bronze--<target>` with a `source` parameter, like
  `verify--silver--normalised`. acnc moves onto it too.
- **D5 Opt-in gate on every unit**, as in `correct-platform-timestamps` 6.10.
  `run_<unit>` jobs gain the `verify` parameter (default `"false"`), a condition
  task, and the bronze and silver verification tasks depend on it; `silver`
  depends on `bronze` and `verify_bronze` with `run_if: NONE_FAILED` (the default
  `ALL_SUCCESS` excluded silver and everything after it in prd when verification
  was off; fixed and tested in `fix-run-acnc-verify-gate`). The default also
  applies in CI, so verification is off in tst/prd runs.
- **D6 Retries off everywhere.** `pipelines.numUpdateRetryAttempts` and
  `pipelines.maxFlowRetryAttempts` set to `"0"` on the 27 pipelines left out of
  #92. The patch is saved from that branch.

## Probes (dev, before relying on the plan)

- **P1** Enabling change data feed through `table_properties` on an SCD2 table
  that already exists and is pipeline-owned (ungm): the property is applied on
  the next update, and the new Landing loads every row once. If it is not
  applied, the reset task runs `ALTER TABLE ... SET TBLPROPERTIES` as the
  pipeline's owner.
- **P2** iso `subdivision_codes`: the deduped view without the stamp gives 0
  writes on an unchanged second load.

## Risks

- ungm and nsw_spatial SCD2 history is kept, so the streaming Landing starts
  from a table that has closed versions (prd nsw_spatial: 7). The first load is a
  snapshot of the whole table, as acnc's was; check Landing equals a full read
  of the SCD2 table.
- nsw_spatial in dev holds 500 rows and in prd 10,007 (row-limited); the
  verification formula must not assume raw equals the source system.
- All five units run in prd after merge. One workload at a time on Free Edition:
  do not merge while another run is active.
