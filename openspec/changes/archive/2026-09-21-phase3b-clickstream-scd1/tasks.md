## 1. Build

- [x] 1.1 Created `src/layers/bronze/clickstream_publish/python/web_events_scd1.py`
      — `create_auto_cdc_flow` (streaming), keyed by `event_id`, sequenced
      by `timestamp`, SCD Type 1
- [x] 1.2 Created `src/layers/bronze/clickstream_publish/sql/web_events_scd1_sql.sql`
      — `AUTO CDC INTO ... FROM STREAM(...)`, same keys/sequence, backtick-
      quoted `` `timestamp` `` to avoid parser ambiguity with the SQL type
      name
- [x] 1.3 Created `clickstream_scd_modeling_python.pipeline.yml` and
      `clickstream_scd_modeling_sql.pipeline.yml`, both targeting
      `bronze_clickstream_publish`

## 2. Validate and run

- [x] 2.1 `databricks bundle validate` passed for dev/tst/prd
- [x] 2.2 `databricks bundle deploy -t dev` — both pipelines "Created"
- [x] 2.3 Ran both against `dev` — both `COMPLETED` on the first attempt,
      no snapshot-workaround needed, confirming the append-only-source
      assumption empirically rather than leaving it inferred
- [x] 2.4 Verified row counts: `web_events_raw` (400), `web_events_scd1`
      (400), `web_events_scd1_sql` (400) — exact match, confirming the
      mechanical-passthrough behavior predicted when this pattern was
      first discussed

## 3. Documentation

- [x] 3.1 Added a note to CLAUDE.md's "Sources" section covering the
      SCD1 tables, why plain streaming Auto CDC works here (unlike Neon),
      and that this was confirmed by running, not assumed
- [x] 3.2 Added `bronze/neon_publish/` and `bronze/clickstream_publish/` to
      CLAUDE.md's repository-structure tree (both were missing —
      `phase3b-neon-scd-modeling` built the former but didn't update the
      tree)
