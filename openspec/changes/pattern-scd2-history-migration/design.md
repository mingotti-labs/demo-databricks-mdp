## Context

An engagement has an SCD2 dimension (`asset_dim_legacy`: one row per version, `start_date`,
`end_date`) kept by hand-written code. It must become a pipeline-owned SCD2 table,
`asset_dim_migrated`, keeping all history. The client's live source is a materialized view
holding the current state (one row per asset) with no change timestamp. The user also wants
the append-only variant, also without a timestamp. The patterns bundle
(`references/patterns/`) holds dev-only reference implementations; its schemas are
`pattern_bronze` and `pattern_bronze_publish` (iac).

## Goals / Non-Goals

**Goals:** history and live changes in one SCD2 table; no stage table; the backfill runs
once and never again on a normal update; one notebook per live-source shape, numbered
steps, runnable in another workspace by changing two widgets; a written guide to
`WITH VERSION`.

**Non-Goals:** the main bundle, CI runs, prd; business dates on live versions (neither
source carries one).

## Decisions

### D1. Each notebook creates everything, including the pipeline file and the pipeline
Agreed with the user. Step 30 writes `asset_dim_migrated.sql` into
`<notebook folder>/transformations/<notebook name>/` (workspace file), with the catalog and
schema filled in from the widgets. Step 55 looks the pipeline up by name and creates it
otherwise with `WorkspaceClient().pipelines.create(...)`: serverless, triggered,
`catalog`/`schema` from the widgets, one `glob` library on that folder. The SQL text lives
once, in the notebook, and is shown in it.
Rejected: a bundle pipeline resource plus a separate `.sql` file (three files to copy).

### D2. Backfill: replay the legacy versions; Auto CDC writes `__START_AT` and `__END_AT`
Same in both notebooks. Auto CDC does not accept `__START_AT`/`__END_AT` as input. It writes
them from the `SEQUENCE BY` value of the events it receives: a new version's `__START_AT` is
the value of the event that created it; an open version's `__END_AT` is the value of the
next event for the same key (a change or a delete).

`asset_history` feeds the legacy dates in as those values. Each legacy version becomes a
change event with `change_ts = start_date`; a version whose `end_date` is set and has no
later version (a retired asset) also becomes a delete event with `change_ts = end_date`:

| legacy row (`asset_dim_legacy`) | event(s) in `asset_history` | result in `asset_dim_migrated` |
|---|---|---|
| A1, Pump, Ann, 2024-01-01, 2024-06-01 | change at 2024-01-01 | Pump, Ann, `__START_AT` 2024-01-01, `__END_AT` 2024-06-01 |
| A1, Pump, Bob, 2024-06-01, null | change at 2024-06-01 | Pump, Bob, `__START_AT` 2024-06-01, `__END_AT` null |
| A2, Valve, Cy, 2024-02-01, 2025-03-01 (retired) | change at 2024-02-01, delete at 2025-03-01 | Valve, Cy, `__START_AT` 2024-02-01, `__END_AT` 2025-03-01 |

In a clean SCD2 table the next `start_date` equals the `end_date`, so every legacy row
arrives with both dates unchanged; step 80 compares them row by row (D7). If the legacy
table closes a version on another date than the next `start_date`, `__END_AT` takes the
next `start_date`; step 80 lists such rows.

```sql
CREATE TEMPORARY VIEW asset_history AS ...;   -- changes and delete events, change_ts TIMESTAMP
CREATE OR REFRESH STREAMING TABLE asset_dim_migrated;
CREATE FLOW backfill_history AS AUTO CDC ONCE INTO asset_dim_migrated
  FROM asset_history KEYS (asset_id) APPLY AS DELETE WHEN is_delete
  SEQUENCE BY change_ts COLUMNS * EXCEPT (is_delete, change_ts) STORED AS SCD TYPE 2;
```
Dates are cast to `TIMESTAMP`: the live flows' versions are timestamps, and flows on one
target share the sequence type. The docs show `AUTO CDC ONCE` only with `FROM SNAPSHOT`;
P1 proves it from a batch view. Fallback: the Python API with `once=True`; the pattern
IDs then end `_python`.
Rejected: `INSERT INTO ONCE` with `__START_AT`/`__END_AT` copied directly (an append flow
into an Auto CDC target is not documented as supported).

### D3. Names and place
Pattern IDs `bronze_publish_scd2_autocdc_backfill_snapshot_sql` and
`bronze_publish_scd2_autocdc_backfill_stream_sql`; notebooks named after them. All tables in
one schema (widget `schema`, default `pattern_bronze_publish`, agreed). Table names are the
engagement's (`asset_dim_legacy`, `asset_source`, `asset_dim_migrated`, plus
`asset_source_base` in the snapshot notebook), so the NAMING.md rule that pattern tables
are named after the pattern ID is waived; the two notebooks share them, so only one
notebook's tables exist at a time. Pipeline display names
`bronze--pattern--publish--scd2--backfill--snapshot--sql--dev` and
`bronze--pattern--publish--scd2--backfill--stream--sql--dev`. The SCD2 columns keep the
Auto CDC names `__START_AT`/`__END_AT` (agreed).

### D4. Snapshot notebook: materialized view source, `WITH VERSION`
- Source: `asset_source_base` (plain Delta table, one row per asset, changed in place) and a
  real materialized view `asset_source AS SELECT asset_id, asset_name, asset_owner FROM
  asset_source_base`, created and refreshed by the notebook (`REFRESH MATERIALIZED VIEW`).
- Live flow:
  ```sql
  CREATE TEMPORARY VIEW asset_live AS SELECT asset_id, asset_name, asset_owner FROM asset_source;
  CREATE FLOW live_snapshot AS AUTO CDC INTO asset_dim_migrated
  FROM SNAPSHOT (SELECT * FROM asset_live)
  WITH VERSION (
    SELECT last_altered AS version
    FROM <catalog>.information_schema.tables
    WHERE table_schema = '<schema>' AND table_name = 'asset_source'
      AND (NOT EXISTS (SELECT 1 FROM last_snapshot_version())
           OR last_altered > (SELECT version FROM last_snapshot_version()))
  )
  KEYS (asset_id)
  STORED AS SCD TYPE 2;
  ```
- Behaviour: one snapshot per refresh of the view. A changed row closes its version and
  opens a new one; a missing asset closes its version (retirement needs no delete event); a
  new asset opens one. Live versions are dated with the view's refresh time, not a business
  date. Several refreshes between two pipeline runs are seen as one: the view keeps only
  the current state.
- A target takes at most one snapshot flow, and a snapshot flow next to regular Auto CDC
  flows needs "snapshot and regular Auto CDC interoperability" (skill reference). P2 proves
  it with the backfill, and that the first update gives the legacy history plus only the
  real differences.
- Fallbacks: if `last_altered` does not move on a refresh, or cannot be read in the version
  query, the Python snapshot flow `dp.create_auto_cdc_from_snapshot_flow(source="asset_live")`
  (each pipeline update is a snapshot, dated with the update time; used by acnc and iso). If
  the first update mixes the flows badly, the notebook writes the live flow into the file
  after the first update.

### D5. Stream notebook: append-only source without a timestamp
- Source: `asset_source` with `delta.enableChangeDataFeed = true`, rows only appended (one
  row per change).
- Live flow:
  ```sql
  CREATE TEMPORARY VIEW asset_live AS
  SELECT asset_id, asset_name, asset_owner, _commit_timestamp AS change_ts, false AS is_delete
  FROM STREAM(asset_source) WITH (readChangeFeed = true)
  WHERE _change_type = 'insert';
  CREATE FLOW live_stream AS AUTO CDC INTO asset_dim_migrated
  FROM STREAM(asset_live) KEYS (asset_id) APPLY AS DELETE WHEN is_delete
  SEQUENCE BY change_ts COLUMNS * EXCEPT (is_delete, change_ts) STORED AS SCD TYPE 2;
  ```
- `_commit_timestamp` is the time the row was written to `asset_source`: fixed, so a full
  refresh replays the changes in the same order. `current_timestamp()` would change on every
  replay. Rejected for that reason.
- Limit: two rows for the same asset in one write share a commit time; their order is
  undefined. The source must write one change per asset per write (stated in step 15).
- Fallback: if SQL cannot stream the change feed, the Python API
  (`spark.readStream.option("readChangeFeed", "true").table(...)`).

### D6. `WITH VERSION`, how it works (goes into the README guide)
- Two queries: a version query returning zero or one row with one orderable value, and a
  snapshot query returning the full table for that version.
- Each pipeline update loops: run the version query; zero rows means stop. Otherwise read
  the snapshot, compare it with the previous one by `KEYS` (changed row: close the old
  version and open a new one; missing key: close; new key: open), write the version value
  as `__START_AT` on new versions and `__END_AT` on closed ones, save the value (returned by
  `last_snapshot_version()` from then on), and repeat.
- Each version must be strictly greater than the previous one; a full refresh clears the
  saved value.
- The version must change only when the data changes. `current_timestamp()` always moves,
  so the version query never returns zero rows and the update never ends. Good versions: a
  file's modification time, an extract date, a view's last refresh time (D4).

### D7. What step 80 checks
- **Backfill matches the legacy table** (after the first update): every `asset_dim_legacy`
  row has a row in `asset_dim_migrated` with the same `asset_id`, `asset_name`,
  `asset_owner`, `__START_AT = start_date` and `__END_AT = end_date` (both null when open),
  and no extra rows other than the live changes the step-20 seed implies. Differences listed.
- **Backfill did not run again**: in `event_log(<pipeline id>)`, the second update has no
  `flow_progress` event with rows written for `backfill_history`, and the backfilled rows are
  identical before and after (count and a hash over all columns, kept in a Python variable).
- **Changes added**: every change made in step 60 is an open version in
  `asset_dim_migrated` and the version it replaced is closed at the same time. Snapshot
  notebook: that time is the view's refresh time, and a deleted asset is closed. Stream
  notebook: that time is the change's `_commit_timestamp`.
- One pass or fail line per check; the cell fails (`assert`) on any failure.
- A full refresh resets the once-only flow and reloads the history; stated, not checked.

### D8. Seed data
Small and fixed (no Faker), so the expected result is readable in the notebook:
- `asset_dim_legacy`: 4 assets, 2 to 3 versions each, 2024 to 2025 dates; one retired.
- Step 20: the current state of the open assets, one of them changed (snapshot: the base
  table; stream: one appended row per open asset). Unchanged rows must open no new version.
- Step 60: one changed asset, one new asset, and in the snapshot notebook one deleted asset.

## Probes

Scripts and output in `references/poc/scd2-history-migration/`, one row each in
`references/docs/registers/probes.md`. Each is a minimal pipeline on a few rows in dev.

- **P1** (both): `AUTO CDC ONCE` from a batch temporary view in SQL; the second update
  writes nothing from it.
- **P2** (snapshot): the notebook can create the materialized view on serverless compute;
  `information_schema.tables.last_altered` changes on each refresh and is readable in the
  version query; the snapshot flow and the backfill share the target; the first update
  gives the legacy history plus only the real differences.
- **P3** (stream): the change feed streams in SQL (`WITH (readChangeFeed = true)`); an
  appended row equal to the current version opens no new version.

## Risks / Trade-offs

- [A probe fails] -> its fallback in D2, D4 or D5; the rest of the design is unchanged.
- [Live version dates are not business dates] -> stated in both notebooks; it follows from
  a source without a timestamp.
- [Table quota at the stop line] -> re-read before the first run; step 90 frees the slots.
- [Pipelines owned by a human] -> dev only and disposable, like the rest of the patterns bundle.
