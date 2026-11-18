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
once, in the notebook, and is shown in it. The pipeline publishes its event log as
`event_log_<pipeline id>` in the schema (1 slot, seen in P1); step 90 drops it with the
tables and the twins.
Rejected: a bundle pipeline resource plus a separate `.sql` file (three files to copy).

### D2. Stream notebook backfill: replay the legacy versions; Auto CDC writes `__START_AT` and `__END_AT`
Stream notebook only (the snapshot notebook backfills inside its one flow, D4). Auto CDC does not accept `__START_AT`/`__END_AT` as input. It writes
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
CREATE TEMPORARY VIEW asset_history AS          -- streaming: P1a
SELECT e.* FROM (
  SELECT explode(CASE WHEN <retired> THEN array(<change>, <delete>) ELSE array(<change>) END) AS e
  FROM STREAM(asset_dim_legacy) l
  JOIN (SELECT asset_id, max(start_date) AS last_start_date
        FROM asset_dim_legacy GROUP BY asset_id) last   -- static lookup
    ON l.asset_id = last.asset_id);
CREATE OR REFRESH STREAMING TABLE asset_dim_migrated;
CREATE FLOW backfill_history AS AUTO CDC ONCE INTO asset_dim_migrated
  FROM STREAM(asset_history) KEYS (asset_id) APPLY AS DELETE WHEN is_delete
  SEQUENCE BY change_ts COLUMNS * EXCEPT (is_delete, change_ts) STORED AS SCD TYPE 2;
```
`<retired>` is `l.end_date IS NOT NULL AND l.start_date = last.last_start_date`. Dates are
cast to `TIMESTAMP`: the live flows' versions are timestamps, and flows on one target share
the sequence type.
**P1 (2026-11-18)**: from a batch view, `AUTO CDC ONCE` fails (P1a: `Source data for the
APPLY CHANGES target ... must be a streaming query`); `ONCE` means "run once", the source
must still be a stream. Hence the streaming view, with the retirement test from a
stream-static join instead of a subquery (P1b). Result: every legacy row arrived with
`__START_AT = start_date` and `__END_AT = end_date`, the retired asset included; the second
update left `backfill_history` `IDLE` and the table unchanged.
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

### D4. Snapshot notebook: one snapshot flow `WITH VERSION` for the backfill and the live loads
- **Why one flow (P2)**: a target fed by a snapshot flow accepts no other flow
  (`MULTI_QUERY_SNAPSHOT_TARGET_NOT_SUPPORTED ... only supports one flow per destination`,
  on the CURRENT and PREVIEW channels). So the once-only backfill of D2 cannot sit next to
  the live snapshot flow; the one snapshot flow does both.
- Source: `asset_source_base` (plain Delta table, one row per asset, changed in place) and a
  real materialized view `asset_source AS SELECT asset_id, asset_name, asset_owner FROM
  asset_source_base`, created and refreshed by the notebook (`REFRESH MATERIALIZED VIEW`).
  A materialized view created from SQL gets its own hidden pipeline: 3 slots (the view,
  its twin, that pipeline's event log; seen in P2).
- Flow:
  ```sql
  CREATE TEMPORARY VIEW asset_history AS        -- legacy versions with their validity
  SELECT asset_id, asset_name, asset_owner,
         CAST(start_date AS TIMESTAMP) AS valid_from, CAST(end_date AS TIMESTAMP) AS valid_to
  FROM asset_dim_legacy;
  CREATE TEMPORARY VIEW asset_live AS           -- the materialized view: current state
  SELECT asset_id, asset_name, asset_owner FROM asset_source;
  CREATE TEMPORARY VIEW asset_union AS          -- both parts; the flow picks one per version
  SELECT asset_id, asset_name, asset_owner, valid_from, valid_to, false AS is_live FROM asset_history
  UNION ALL
  SELECT asset_id, asset_name, asset_owner, NULL, NULL, true FROM asset_live;
  CREATE TEMPORARY VIEW asset_versions AS       -- every version to process
  SELECT valid_from AS version, false AS is_live FROM asset_history
  UNION SELECT valid_to, false FROM asset_history WHERE valid_to IS NOT NULL
  UNION SELECT last_altered, true FROM <catalog>.information_schema.tables
        WHERE table_schema = '<schema>' AND table_name = 'asset_source';
  CREATE TEMPORARY VIEW asset_cutover AS        -- the last legacy version
  SELECT max(version) AS last_legacy_version FROM asset_versions WHERE NOT is_live;

  CREATE OR REFRESH STREAMING TABLE asset_dim_migrated;
  CREATE FLOW migrate_and_load AS AUTO CDC INTO asset_dim_migrated
  FROM SNAPSHOT (                               -- v = (SELECT version FROM current_snapshot_version())
    SELECT u.asset_id, u.asset_name, u.asset_owner
    FROM asset_union u CROSS JOIN asset_cutover c
    WHERE CASE WHEN u.is_live THEN v > c.last_legacy_version
               ELSE v <= c.last_legacy_version AND u.valid_from <= v
                    AND (u.valid_to IS NULL OR u.valid_to > v) END
  )
  WITH VERSION (
    SELECT min(version) AS version FROM asset_versions
    WHERE NOT EXISTS (SELECT 1 FROM last_snapshot_version())
       OR version > (SELECT version FROM last_snapshot_version())
    HAVING min(version) IS NOT NULL
  )
  KEYS (asset_id)
  STORED AS SCD TYPE 2;
  ```
- The union is a view (`asset_union`, the user's idea); only the filter on the version
  stays inside `FROM SNAPSHOT`, because `current_snapshot_version()` works only there.
- Behaviour, first update: one snapshot per distinct legacy date, in order (the assets
  valid on that date), then one for the view. Every legacy `start_date` and `end_date`
  lands in `__START_AT`/`__END_AT`; a retired asset is missing from the snapshot on its
  `end_date`, so it is closed then (no delete event). Later updates: the saved version is
  past every legacy date, so only a new refresh of the view is processed; the history is
  never read again. Live versions are dated with the view's refresh time, not a business
  date; several refreshes between two runs are seen as one.
- Cost: see D6, "Performance".
- `current_snapshot_version()` must be called in a plain scalar subquery each time it is
  needed (`v` above); inside a `WITH` (CTE) it is not resolved (P2c-a:
  `UNRESOLVABLE_TABLE_VALUED_FUNCTION`). The pipeline ran on runtime 18.3 (CURRENT channel).
- **P2c (2026-11-18), passed**: update 1 gave the legacy rows with exact dates (the retired
  asset closed at its `end_date`), closed and opened only the asset the view changed, at the
  view's `last_altered`, and left the unchanged asset alone; after changes and `REFRESH
  MATERIALIZED VIEW`, `last_altered` moved and update 2 applied a change, a delete and an
  insert at that time; update 3 without a refresh changed nothing (4 seconds). The first
  update took about 2 minutes for 6 versions (about 20 seconds per version, Free Edition).
- Fallbacks (not needed in P2c): if the snapshot query cannot read temporary views, the union is
  written inline in it; if `last_altered` does not move on a refresh, or cannot be read in
  the version query, the version of the live part becomes the pipeline update's time in a
  Python snapshot flow with a version function (`dp.create_auto_cdc_from_snapshot_flow`
  with a callable source).

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
- **Performance**: every version is a full comparison of the snapshot against the previous
  one, committed on its own. A first update that replays history costs about
  *number of distinct dates x rows per snapshot*: 20 monthly batches of 1 million rows is
  20 comparisons; 5 years of business-day changes on 50,000 rows is about 1,250 commits
  and may take hours. Measured in P2c on Free Edition serverless: about 20 seconds per
  version on 5 rows, so a fixed cost per version dominates small snapshots (1,250 dates
  would be about 7 hours). After that, each update compares one snapshot. Measure first:
  `count(DISTINCT start_date)` plus `count(DISTINCT end_date)` of the legacy table (the
  number of distinct dates is not known for the client yet). Many dates: test the first
  update on a copy at full size before the cut-over, or let the first update run as its
  own job before the pipeline is scheduled.

### D7. What step 80 checks
- **Backfill matches the legacy table** (after the first update): every `asset_dim_legacy`
  row has a row in `asset_dim_migrated` with the same `asset_id`, `asset_name`,
  `asset_owner`, `__START_AT = start_date` and `__END_AT = end_date` (both null when open),
  and no extra rows other than the live changes the step-20 seed implies. Differences listed.
- **Backfill did not run again**: the backfilled rows are identical before and after the
  second update (count and a hash over all columns, kept in a Python variable). Stream
  notebook: the event log shows `backfill_history` `IDLE` in the second update (as in P1).
  Snapshot notebook: the versions processed by the second update are all later than the
  last legacy version.
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
- **P2** (snapshot): can a snapshot flow share the target with the once-only backfill? No
  (D4); the view's `last_altered` could be read once after creation, the rest was not
  reached.
- **P2c** (snapshot): the one flow of D4. Does the snapshot query read the temporary views;
  does `last_altered` move on a refresh and work in the version query; does the first
  update give the legacy history with its dates plus only the real differences; does an
  update without a refresh process nothing? Also: can a serverless notebook create the
  materialized view (checked in the notebook run)?
- **P3** (stream): the change feed streams in SQL (`WITH (readChangeFeed = true)`); an
  appended row equal to the current version opens no new version.

## Risks / Trade-offs

- [A probe fails] -> its fallback in D2, D4 or D5; the rest of the design is unchanged.
- [Many distinct legacy dates make the first snapshot update slow] -> measure first (D6).
- [Live version dates are not business dates] -> stated in both notebooks; it follows from
  a source without a timestamp.
- [Table quota at the stop line] -> re-read before the first run; step 90 frees the slots.
- [Pipelines owned by a human] -> dev only and disposable, like the rest of the patterns bundle.
