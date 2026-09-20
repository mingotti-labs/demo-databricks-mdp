## Context

See proposal.md - Why. This is the "history via SCD in `_publish`" half of
`phase3b-bronze-schema-simplification`'s design — that change removed
`bronze_neon_history` on the premise that `<table>_scd2` tables would
replace its purpose. This change builds that.

The initial design (documented in the original proposal draft, before this
was corrected mid-implementation) assumed streaming Auto CDC
(`create_auto_cdc_flow`) would work directly against `bronze_neon.*_raw`,
mirroring the reference examples in the `databricks-pipelines` skill. That
assumption was wrong, discovered via a real failure, and the design changed
as a direct result — recorded here rather than silently rewritten.

## Goals / Non-Goals

**Goals:**
- Correct SCD1 and SCD2 modeling for Neon's tables, genuinely verified with
  a real before/after update — not just initial-load row counts
- Both languages, matching what a source shaped like `bronze_neon.*_raw`
  (upsert-maintained, not append-only) actually supports in each

**Non-Goals:**
- Restructuring `neon_ecommerce_ingestion` itself — it stays exactly as
  it is; this change only reads from its output
- SCD2 for `orders`/`order_items` — not dimension-like, no real value in
  tracking their full history the way customer/product attributes matter

## Decisions

**Streaming Auto CDC (`create_auto_cdc_flow`) does not work against
`bronze_neon.*_raw` — confirmed via a real failure, not assumed.**
`bronze_neon.customers_raw` is populated by `neon_ecommerce_ingestion` using
`cursor_columns: [updated_at]` — when a row changes, Lakeflow Connect
`MERGE`s the new values into the existing row (same key), not appends a new
row. A genuine customer-email update produced a real Delta `UPDATE` commit
against `customers_raw`. Streaming Auto CDC's underlying `readStream` then
failed with `[DELTA_SOURCE_TABLE_IGNORE_CHANGES] ... streaming tables may
only use an append-only stream source` the moment it encountered that
commit — Spark Structured Streaming's default protection against silently
misinterpreting non-append changes on a Delta source.

**`skipChangeCommits` considered and rejected.**
The obvious-looking fix for "streaming read hits a non-append commit" is
`.option("skipChangeCommits", "true")`. Checked against Databricks'
documentation before using it: it "ignores update/delete commits on the
upstream" — meaning it doesn't crash, but the rows affected by those commits
are **silently dropped from the stream entirely**, never re-emitted. Using
it here would make the pipeline "work" (no error) while never actually
capturing a single customer or product change — worse than the crash, since
it fails silently instead of loudly. Rejected.

**Python: `create_auto_cdc_from_snapshot_flow` against a batch snapshot.**
This compares two full snapshots (this run vs. the last) rather than
streaming change events, computing inserts/updates itself. It doesn't
attempt a streaming read at all, so the append-only requirement doesn't
apply — it matches what `bronze_neon.*_raw` actually is: a continuously
upserted "current state" table, not a change-event log. Implemented via a
`@dp.materialized_view()` per source table (a batch `spark.read.table(...)`)
feeding `source=` on the snapshot flow, per the documented pattern.

**SQL SCD1: no CDC at all, a plain passthrough materialized view.**
`bronze_neon.customers_raw` is already "latest value per key" by
construction (that's what upsert-maintained means) — which is the literal
definition of SCD1. `CREATE OR REFRESH MATERIALIZED VIEW customers_scd1_sql
AS SELECT * FROM bronze_neon.customers_raw` already satisfies the
requirement; invoking `AUTO CDC INTO` for this would be solving a problem
that doesn't exist.

**SQL SCD2: a hand-rolled two-phase `MERGE`, running as a job, not a
pipeline dataset.**
SQL's `AUTO CDC INTO` supports streaming sources only — Databricks' own
docs are explicit that snapshot-based CDC (the Python fix above) has no SQL
equivalent. Since `MERGE` statements aren't valid inside a declarative
streaming-table/materialized-view body, this genuinely cannot be expressed
as a `.pipeline.yml` dataset at all. The real SQL-native answer, confirmed
against well-established Delta Lake documentation (not invented for this
project), is the classic two-phase `MERGE`: Phase A expires the active
version of any row whose tracked columns changed (sets `__END_AT`); Phase B
inserts a new active version for anything new or just-expired. Implemented
as two Python-notebook tasks (thin `spark.sql()` wrappers for catalog
parameterization — the `MERGE` statements themselves are the actual pattern)
in one job, `neon_scd2_merge_sql`.

## Risks / Trade-offs

- [The SQL SCD2 job's first-ever run against a given target can't produce
  history for rows that changed before the job's target table existed — it
  only detects changes between ITS OWN successive runs, not the source's
  full history] → Mitigation: this is inherent to any diff-based
  (non-CDF) SCD2 approach, not a bug; documented and demonstrated directly —
  the first run against `dev` captured current state as an initial baseline
  with no prior version, and a second run (after a real update) correctly
  produced two tracked versions with proper `__START_AT`/`__END_AT`.
- [Two Auto CDC flows (SCD1 and SCD2, Python) each read their own
  materialized-view snapshot of the same source table — some duplicate
  compute] → Mitigation: acceptable for this project's scale; a shared
  snapshot MV consumed by both flows was considered but kept separate here
  since it's simpler to reason about per-flow and the tables are small.

## Migration Plan

Additive only. Deploy, run the Python pipeline and SQL pipeline (dev),
confirm initial-load row counts match source exactly, then prove SCD1 vs
SCD2 behavior for real: update one row in Neon, re-run ingestion, re-run
the SCD flows (Python pipeline, SQL pipeline, SQL merge job), confirm SCD1
shows the overwritten value and SCD2 shows two correctly-bounded versions —
done for both languages, not just one. Rollback: drop the new resources;
nothing else depends on them.
