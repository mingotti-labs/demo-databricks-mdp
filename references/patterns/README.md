# Patterns bundle

Deployable reference implementations that are not part of any source's flow. Dev only; the
main bundle excludes `references/**`. Pipelines write to `pattern_bronze` and
`pattern_bronze_publish` (created by iac). Nothing here runs in CI except
`databricks bundle validate`.

Unlike the main bundle, you deploy this one yourself, from this folder:

```
cd references/patterns
databricks bundle validate -t dev --profile <PROFILE>
databricks bundle deploy   -t dev --profile <PROFILE>
```

Deploying creates pipelines and jobs, not tables. Tables, and so table slots, appear only
when you run a pipeline. The metastore holds 500 tables; a streaming table or materialized
view costs 2 slots (it has a hidden `__materialization_mat_*` twin). Check
`databricks resource-quotas get-quota metastore <metastore_id> table-quota` first.

## Lakeflow Connect, query-based, PostgreSQL (`bronze_lakeflow_query_postgresql`)

Managed ingestion pipeline reading Neon through the UC connection `neon_dev`, polling each
table by its `updated_at` column. No gateway, so no classic compute. Hard deletes at the
source are not propagated; a new table needs a new `table:` block.
Needs the live Neon project, the connection `neon_dev` and secret scope `neon-postgres` (iac).
Slots: about 9 while the tables exist (4 tables with twins, plus the pipeline's own).

```
databricks bundle run pattern_seed_neon                       --profile <PROFILE>   # reseeds Neon
databricks bundle run pattern_bronze_lakeflow_query_postgresql --profile <PROFILE>   # tables pattern_bronze.lakeflow_query_postgresql_*
databricks bundle run pattern_verify_lakeflow_query_postgresql --profile <PROFILE>   # row counts equal Neon's
```

Remove: `databricks bundle destroy -t dev --profile <PROFILE>` deletes the pipeline, and
Lakeflow Connect drops its tables with it, but not their hidden `__materialization_mat_*`
twins. Run `references/poc/table-cleanup/find_orphans.py --profile <PROFILE>` and drop the
`ORPHAN` twins it lists (`drop_tables.py` in the same folder).

## Auto Loader, `addNewColumns` (`bronze_autoloader_add_new_columns_python`)

Streaming table over JSON files in the volume `bronze_clickstream.s3_clickstream_raw` (iac),
with the schema evolution write-up in the file. The same volume feeds the other seven
Auto Loader variants in `src/bronze/`. Slots: 2.

```
databricks bundle run pattern_seed_clickstream_events           --profile <PROFILE>   # appends a batch of files; run it again later for a batch with a new column
databricks bundle run pattern_bronze_autoloader_add_new_columns_python --profile <PROFILE>
databricks bundle run pattern_verify_autoloader                 --profile <PROFILE>
```

A new column in a later batch stops the running update once, and Databricks starts a new one
by itself; the first `bundle run` that sees it reports a failure even though the pipeline recovers.

Remove: `databricks bundle destroy -t dev --profile <PROFILE>`, then drop what it leaves
(a regular pipeline's tables stay, with their twins):

```
DROP TABLE mdp_dev.pattern_bronze.autoloader_add_new_columns_python;
```

and the hidden `__materialization_mat_*` twin that `find_orphans.py` lists for it.

## Patterns that read another pattern

Run the source pattern first.

| Pattern | Reads |
|---|---|
| `bronze_publish_scd1_autocdc_stream_sql` | `pattern_bronze.autoloader_add_new_columns_python` |
| `bronze_publish_scd1_materialized_view_sql` | `pattern_bronze.lakeflow_query_postgresql_customers` |
| `bronze_publish_scd2_merge_sql` (job) | `pattern_bronze.lakeflow_query_postgresql_customers` |

After running any patterns, `databricks bundle run tag_patterns` sets each table's
`design_pattern` tag (register: `references/docs/registers/design-patterns.md`).

## SCD2 migration with history, no stage table (`bronze_publish_scd2_autocdc_backfill_*_sql`)

Four notebooks in `src/bronze_publish/` move a legacy SCD2 dimension (`asset_dim_legacy`, with
`start_date`/`end_date`) and its history into a pipeline-owned SCD2 table (`asset_dim_migrated`), then keep
it current from a live source that has no change timestamp. Each notebook does every step (10 to 90): it
creates and seeds the tables, writes `asset_dim_migrated.sql` into `transformations/<notebook>/` next to
itself, creates (or reuses, with a full refresh) the pipeline, runs it twice and checks the result.
To use them elsewhere, change the `catalog` and `schema` widgets and point the views at the real tables.
Run one notebook at a time: they use the same table names. `teardown = true` runs step 90, which deletes the
pipeline and drops the tables, their hidden twins and event logs.

| Notebook | Live source | Flows | Slots while it exists |
|---|---|---|---|
| `..._snapshot_sql` | materialized view (current state only) | one snapshot flow `WITH VERSION`: every legacy date, then each refresh of the view | 8 |
| `..._stream_sql` | append-only table, change data feed on | `AUTO CDC ONCE` backfill + streaming Auto CDC over the change feed (`_commit_timestamp`) | 5 |
| `..._snapshot_sid_sql` | materialized view; legacy table has a surrogate key `asset_sid` | as `..._snapshot_sql`, with the key (below) | 8 |
| `..._snapshot_sid_unique_sql` | as `..._snapshot_sid_sql` | as `..._snapshot_sid_sql`, plus the view `asset_dim_unique` | 8 + the view |

### Surrogate key (`..._sid_sql`, `..._sid_unique_sql`)

- Both sides hash the row's own values: `row_hash` = SHA-256 text of `asset_id`, `asset_name`,
  `asset_owner` (an empty value hashes as `<null>`). The history keeps its keys.
- A live row reuses the key of the newest legacy row with the same `row_hash` when that row is still
  open; otherwise its key is `xxhash64(row_hash)` (BIGINT). An unchanged row keeps the open legacy key,
  so the first live snapshot opens no version for it.
- Risk (accepted in `..._sid_sql`): a row that changes back to earlier values gets that earlier key
  again, one key on two versions. The pipeline cannot read its own target to tell (`Graph is not
  topologically sorted ... cycle`, probe P4).
- `..._sid_unique_sql` adds the view `asset_dim_unique`: the stored key up to the cut-over (the last
  legacy date), `xxhash64(row_hash, __START_AT)` after it, so one key per version. Consumers read the view.

Skills that write the pipeline `.sql` file for each of the four notebooks: `references/skills/`.

Run in dev as a one-time serverless job with `max_retries: 0` (a failed run is otherwise retried from the
top), or interactively.

### `WITH VERSION`, how it works

- Two queries: a **version query** returning zero or one row with one orderable value, and a **snapshot
  query** returning the full table for that version.
- Each pipeline update loops: run the version query (no row: stop); read the snapshot; compare it with the
  previous one by `KEYS` (changed row: close the old version, open a new one; missing key: close; new key:
  open); write the version as `__START_AT` on new versions and `__END_AT` on closed ones; save it
  (`last_snapshot_version()`); repeat.
- Versions must only increase; a full refresh forgets the saved one.
- The version must change only when the data changes. `current_timestamp()` always moves, so the update
  never ends. Good versions: a file's modification time, an extract date, a view's refresh time
  (`information_schema.tables.last_altered`).
- In the snapshot notebook the union of legacy and live rows is a temporary view (`asset_union`, with an
  `is_live` flag); only the filter on the version stays inside `FROM SNAPSHOT`. Columns used only in that
  filter do not reach the target.

**Performance.** Each version is a full comparison, committed on its own: about 20 s per version on Free
Edition. The first update of the snapshot notebook costs one version per distinct legacy date, so measure
first (`count(DISTINCT start_date)` plus `count(DISTINCT end_date)`; step 25 prints it): 20 monthly batches
take minutes, 1,250 business days about 7 hours. With many dates, try the first update on a full-size copy
before the cut-over. After the first update, each run processes only new refreshes.

### Limits found (probes in `references/poc/scd2-history-migration/`)

- `AUTO CDC ONCE` needs a streaming source, even though it runs once (`... must be a streaming query`).
- A table fed by a snapshot flow takes no other flow (`MULTI_QUERY_SNAPSHOT_TARGET_NOT_SUPPORTED`, current
  and preview channels): the backfill and the live snapshot must be one flow.
- `current_snapshot_version()` works in plain subqueries, not inside a `WITH` clause.
- A materialized view created from SQL has its own hidden pipeline: 3 slots. A pipeline created through the
  API publishes `event_log_<id>` in its schema. The tables API does not list twins or event logs; use
  `information_schema` to find them.
- The SDK on serverless notebooks has no folder (glob) library class; the notebooks create the pipeline
  through the REST API.
