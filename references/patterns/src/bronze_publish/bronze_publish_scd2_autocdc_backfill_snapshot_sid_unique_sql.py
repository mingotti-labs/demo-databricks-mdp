# Databricks notebook source
# MAGIC %md
# MAGIC # SCD2 migration with history and one surrogate key per version, live source = materialized view
# MAGIC
# MAGIC Pattern `bronze_publish_scd2_autocdc_backfill_snapshot_sid_unique_sql`. The same migration as
# MAGIC `bronze_publish_scd2_autocdc_backfill_snapshot_sql` (one Auto CDC snapshot flow `WITH VERSION`:
# MAGIC every legacy date, then each refresh of the view), for a legacy table that also has a
# MAGIC surrogate key `asset_sid` (BIGINT) per version.
# MAGIC
# MAGIC **The key rule.** Both sides compute `row_hash`, a SHA-256 text hash of the row's own values
# MAGIC (`asset_id`, `asset_name`, `asset_owner`; an empty value hashes as `<null>`). The history keeps
# MAGIC its keys. A live row looks its `row_hash` up among the legacy rows, newest `start_date` first
# MAGIC (a duplicate left by an error counts once), and reuses that key only when that legacy row is
# MAGIC still open. Otherwise the key is new: `xxhash64(row_hash)`, a BIGINT.
# MAGIC
# MAGIC An unchanged live row therefore carries the same key as the open legacy version, so the first
# MAGIC live snapshot opens no version for it (the key is a tracked column like the others).
# MAGIC
# MAGIC **Why a view on top.** The snapshot reads the legacy table and the live view, nothing of
# MAGIC its own past, so the stored key cannot tell "unchanged since the cut-over" from "changed and
# MAGIC changed back": a row that returns to earlier values gets that earlier key again (pattern
# MAGIC `..._snapshot_sid_sql`, which accepts this). The pipeline cannot read its own target to tell
# MAGIC either (probe P4 variant B: `Graph is not topologically sorted ... cycle`). So step 85 adds the
# MAGIC view `asset_dim_unique`: up to the cut-over the stored (legacy) key, after it
# MAGIC `xxhash64(row_hash, __START_AT)`, one key per version. Read the dimension through the view.
# MAGIC
# MAGIC Run the steps in order. To copy to another workspace, change the `catalog` and `schema`
# MAGIC widgets. Step 90 removes everything when `teardown` is `true`.

# COMMAND ----------

dbutils.widgets.text("catalog", "mdp_dev")
dbutils.widgets.text("schema", "pattern_bronze_publish")
dbutils.widgets.dropdown("teardown", "false", ["false", "true"])
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
teardown = dbutils.widgets.get("teardown") == "true"

target = f"{catalog}.{schema}"
legacy = f"{target}.asset_dim_legacy"
base = f"{target}.asset_source_base"
source = f"{target}.asset_source"
migrated = f"{target}.asset_dim_migrated"
unique = f"{target}.asset_dim_unique"
pipeline_name = f"bronze--pattern--publish--scd2--backfill--snapshot--sid--unique--sql--{schema}"

notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
pipeline_folder = f"/Workspace{notebook_path.rsplit('/', 1)[0]}/transformations/{notebook_path.rsplit('/', 1)[1]}"
pipeline_file = f"{pipeline_folder}/asset_dim_migrated.sql"
print(target, pipeline_file, sep="\n")

# The row's own values, hashed the same way in the pipeline and in the checks.
ROW_HASH = """sha2(concat_ws('|', coalesce(asset_id, '<null>'), coalesce(asset_name, '<null>'),
                      coalesce(asset_owner, '<null>')), 256)"""

# COMMAND ----------

import io
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

w = WorkspaceClient()


def run_pipeline(pipeline_id: str, full_refresh: bool = False) -> str:
    """Start an update, wait for it to finish, print errors, return the update id."""
    update_id = w.pipelines.start_update(pipeline_id, full_refresh=full_refresh).update_id
    while True:
        state = w.pipelines.get_update(pipeline_id, update_id).update.state.value
        if state in ("COMPLETED", "FAILED", "CANCELED"):
            break
        time.sleep(15)
    print(f"update {update_id}: {state}")
    if state != "COMPLETED":
        for e in w.pipelines.list_pipeline_events(pipeline_id, max_results=100):
            if e.level and e.level.value == "ERROR" and e.error:
                for ex in e.error.exceptions or []:
                    print("ERROR:", (ex.message or "")[:800])
        raise RuntimeError(f"pipeline update {state}")
    return update_id


def last_altered(table: str) -> str:
    """The refresh time of a materialized view, as information_schema reports it."""
    return spark.sql(f"""
        SELECT last_altered FROM {catalog}.information_schema.tables
        WHERE table_schema = '{schema}' AND table_name = '{table}'
    """).first()[0]


def new_key(asset_id: str, asset_name: str, asset_owner: str) -> int:
    """The key the pipeline gives a version that has no open legacy key."""
    return spark.sql(f"""
        SELECT xxhash64({ROW_HASH}) FROM VALUES ('{asset_id}', '{asset_name}', '{asset_owner}')
        AS t(asset_id, asset_name, asset_owner)
    """).first()[0]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 10: the legacy SCD2 dimension, with its surrogate key

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {legacy} (
  asset_sid BIGINT, asset_id STRING, asset_name STRING, asset_owner STRING, start_date DATE, end_date DATE
)
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 15: the live source, a materialized view without a timestamp or a key
# MAGIC
# MAGIC `asset_source_base` stands in for whatever the client's view reads; the notebook changes
# MAGIC it in place. `asset_source` is a real materialized view (3 table slots: the view, its hidden
# MAGIC twin and its own pipeline's event log).

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {base} (asset_id STRING, asset_name STRING, asset_owner STRING)
""")
spark.sql(f"""
CREATE OR REPLACE MATERIALIZED VIEW {source} AS
SELECT asset_id, asset_name, asset_owner FROM {base}
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 20: seed the live source (current state: A3 changed since the legacy table)

# COMMAND ----------

spark.sql(f"""
INSERT INTO {base} VALUES
  ('A1', 'Pump', 'Cid'),
  ('A3', 'Fan',  'Hal'),
  ('A4', 'Belt', 'Gil')
""")
spark.sql(f"REFRESH MATERIALIZED VIEW {source}")
refresh_20 = last_altered("asset_source")
print("view refreshed at", refresh_20)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 25: seed the legacy history
# MAGIC
# MAGIC A2 retired on 2025-03-01. A3 had owner Eli twice (keys 301 and 303): the live lookup takes
# MAGIC the newest, 303, which is open.

# COMMAND ----------

spark.sql(f"""
INSERT INTO {legacy} VALUES
  (101, 'A1', 'Pump',  'Ann', DATE'2024-01-01', DATE'2024-06-01'),
  (102, 'A1', 'Pump',  'Bob', DATE'2024-06-01', DATE'2025-01-15'),
  (103, 'A1', 'Pump',  'Cid', DATE'2025-01-15', NULL),
  (201, 'A2', 'Valve', 'Cy',  DATE'2024-02-01', DATE'2024-09-01'),
  (202, 'A2', 'Valve', 'Dan', DATE'2024-09-01', DATE'2025-03-01'),
  (301, 'A3', 'Fan',   'Eli', DATE'2024-03-01', DATE'2024-08-01'),
  (302, 'A3', 'Fan',   'Di',  DATE'2024-08-01', DATE'2025-05-01'),
  (303, 'A3', 'Fan',   'Eli', DATE'2025-05-01', NULL),
  (401, 'A4', 'Belt',  'Flo', DATE'2024-04-01', DATE'2024-10-01'),
  (402, 'A4', 'Belt',  'Gil', DATE'2024-10-01', NULL)
""")
display(spark.sql(f"""
SELECT count(*) AS legacy_rows, count(DISTINCT asset_id) AS assets,
       (SELECT count(*) FROM (SELECT start_date FROM {legacy}
                              UNION SELECT end_date FROM {legacy} WHERE end_date IS NOT NULL)) AS distinct_dates
FROM {legacy}
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 30: the pipeline file and its target
# MAGIC
# MAGIC The notebook writes `asset_dim_migrated.sql` into `transformations/<notebook name>/` next to
# MAGIC itself; the pipeline (step 55) reads that file. Steps 40 and 50 add to it.

# COMMAND ----------

def write_pipeline_file(text: str) -> None:
    w.workspace.mkdirs(pipeline_folder)
    w.workspace.upload(pipeline_file, io.BytesIO(text.encode()), format=ImportFormat.RAW, overwrite=True)


sql_target = """-- Written by the notebook bronze_publish_scd2_autocdc_backfill_snapshot_sid_unique_sql (step 30).
CREATE OR REFRESH STREAMING TABLE asset_dim_migrated;
"""
write_pipeline_file(sql_target)
print(sql_target)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 40: the views
# MAGIC
# MAGIC - `asset_history`: each legacy version with its key and the dates it was valid.
# MAGIC - `asset_legacy_key`: per `row_hash`, the key of the newest legacy row, only if it is open.
# MAGIC - `asset_live`: the materialized view (current state) with a key: the open legacy key, or new.
# MAGIC - `asset_union`: both; the flow picks one part per version.
# MAGIC - `asset_versions`: every version to process: each legacy date, then the view's refresh time.
# MAGIC - `asset_cutover`: the last legacy date.

# COMMAND ----------

sql_views = f"""
CREATE TEMPORARY VIEW asset_history AS
SELECT asset_sid, asset_id, asset_name, asset_owner,
       CAST(start_date AS TIMESTAMP) AS valid_from, CAST(end_date AS TIMESTAMP) AS valid_to,
       {ROW_HASH} AS row_hash
FROM {legacy};

CREATE TEMPORARY VIEW asset_legacy_key AS
SELECT row_hash, asset_sid
FROM (SELECT row_hash, asset_sid, valid_to,
             row_number() OVER (PARTITION BY row_hash ORDER BY valid_from DESC) AS rank
      FROM asset_history)
WHERE rank = 1 AND valid_to IS NULL;

CREATE TEMPORARY VIEW asset_live AS
SELECT coalesce(k.asset_sid, xxhash64(l.row_hash)) AS asset_sid,
       l.asset_id, l.asset_name, l.asset_owner
FROM (SELECT asset_id, asset_name, asset_owner, {ROW_HASH} AS row_hash FROM {source}) l
LEFT JOIN asset_legacy_key k ON k.row_hash = l.row_hash;

CREATE TEMPORARY VIEW asset_union AS
SELECT asset_sid, asset_id, asset_name, asset_owner, valid_from, valid_to, false AS is_live
FROM asset_history
UNION ALL
SELECT asset_sid, asset_id, asset_name, asset_owner, CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP), true
FROM asset_live;

CREATE TEMPORARY VIEW asset_versions AS
SELECT valid_from AS version, false AS is_live FROM asset_history
UNION SELECT valid_to, false FROM asset_history WHERE valid_to IS NOT NULL
UNION SELECT last_altered, true FROM {catalog}.information_schema.tables
      WHERE table_schema = '{schema}' AND table_name = 'asset_source';

CREATE TEMPORARY VIEW asset_cutover AS
SELECT max(version) AS last_legacy_version FROM asset_versions WHERE NOT is_live;
"""
write_pipeline_file(sql_target + sql_views)
print(sql_views)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 50: the flow (backfill, then live)
# MAGIC
# MAGIC As in the snapshot notebook, with `asset_sid` as the first column. `current_snapshot_version()`
# MAGIC must be called in plain subqueries; inside a `WITH` clause it is not resolved.

# COMMAND ----------

sql_flow = """
CREATE FLOW migrate_and_load AS AUTO CDC INTO asset_dim_migrated
FROM SNAPSHOT (
  SELECT u.asset_sid, u.asset_id, u.asset_name, u.asset_owner
  FROM asset_union u CROSS JOIN asset_cutover c
  WHERE CASE WHEN u.is_live
             THEN (SELECT version FROM current_snapshot_version()) > c.last_legacy_version
             ELSE (SELECT version FROM current_snapshot_version()) <= c.last_legacy_version
                  AND u.valid_from <= (SELECT version FROM current_snapshot_version())
                  AND (u.valid_to IS NULL
                       OR u.valid_to > (SELECT version FROM current_snapshot_version())) END
)
WITH VERSION (
  SELECT min(version) AS version FROM asset_versions
  WHERE NOT EXISTS (SELECT 1 FROM last_snapshot_version())
     OR version > (SELECT version FROM last_snapshot_version())
  HAVING min(version) IS NOT NULL
)
KEYS (asset_id)
STORED AS SCD TYPE 2;
"""
write_pipeline_file(sql_target + sql_views + sql_flow)
print(sql_flow)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 55: create (or reuse) the pipeline and run it
# MAGIC
# MAGIC Steps 10 to 25 recreate the tables, so a reused pipeline runs a full refresh: it forgets
# MAGIC its saved version and rebuilds `asset_dim_migrated` from the legacy dates again.

# COMMAND ----------

existing = [p for p in w.pipelines.list_pipelines(filter=f"name LIKE '{pipeline_name}'")]
if existing:
    pipeline_id = existing[0].pipeline_id
    print("reusing pipeline", pipeline_id, "(full refresh)")
else:
    # REST call: the SDK on serverless notebooks may predate folder (glob) libraries.
    pipeline_id = w.api_client.do("POST", "/api/2.0/pipelines", body={
        "name": pipeline_name,
        "catalog": catalog,
        "schema": schema,
        "serverless": True,
        "continuous": False,
        "configuration": {"pipelines.numUpdateRetryAttempts": "0"},
        "libraries": [{"glob": {"include": f"{pipeline_folder}/**"}}],
    })["pipeline_id"]
    print("created pipeline", pipeline_id)

first_update = run_pipeline(pipeline_id, full_refresh=bool(existing))
spark.sql(f"ALTER STREAMING TABLE {migrated} SET TAGS ('design_pattern' = 'bronze_publish_scd2_autocdc_backfill_snapshot_sid_unique_sql')")
cutover = spark.sql(f"""
SELECT max(d) FROM (SELECT start_date AS d FROM {legacy} UNION SELECT end_date FROM {legacy})
""").first()[0]

# The history part: rows started on a legacy date, with __END_AT only when a legacy date closed them.
HISTORY_HASH = f"""
SELECT count(*) AS n,
       sum(hash(asset_sid, asset_id, asset_name, asset_owner, __START_AT,
                CASE WHEN __END_AT <= TIMESTAMP'{cutover}' THEN __END_AT END)) AS h
FROM {migrated} WHERE __START_AT <= TIMESTAMP'{cutover}'
"""
history_after_first = spark.sql(HISTORY_HASH).first()
display(spark.sql(f"SELECT * FROM {migrated} ORDER BY asset_id, __START_AT"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 60: change the source (A1 new owner, A4 removed, A5 new) and refresh the view

# COMMAND ----------

spark.sql(f"UPDATE {base} SET asset_owner = 'Ivy' WHERE asset_id = 'A1'")
spark.sql(f"DELETE FROM {base} WHERE asset_id = 'A4'")
spark.sql(f"INSERT INTO {base} VALUES ('A5', 'Motor', 'Jo')")
spark.sql(f"REFRESH MATERIALIZED VIEW {source}")
refresh_60 = last_altered("asset_source")
print("view refreshed at", refresh_60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 70: run the pipeline again

# COMMAND ----------

second_update = run_pipeline(pipeline_id)
display(spark.sql(f"SELECT * FROM {migrated} ORDER BY asset_id, __START_AT"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 75: the known risk: A1 goes back to its open legacy owner (Cid)

# COMMAND ----------

spark.sql(f"UPDATE {base} SET asset_owner = 'Cid' WHERE asset_id = 'A1'")
spark.sql(f"REFRESH MATERIALIZED VIEW {source}")
refresh_75 = last_altered("asset_source")
print("view refreshed at", refresh_75)
third_update = run_pipeline(pipeline_id)
display(spark.sql(f"SELECT * FROM {migrated} WHERE asset_id = 'A1' ORDER BY __START_AT"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 80: checks

# COMMAND ----------

results = []

mismatches = spark.sql(f"""
SELECT l.*, m.__START_AT, m.__END_AT
FROM {legacy} l LEFT JOIN {migrated} m
  ON m.asset_sid = l.asset_sid AND m.asset_id = l.asset_id AND m.asset_name = l.asset_name
 AND m.asset_owner = l.asset_owner AND m.__START_AT = CAST(l.start_date AS TIMESTAMP)
WHERE m.asset_id IS NULL
   OR (l.end_date IS NOT NULL AND NOT m.__END_AT <=> CAST(l.end_date AS TIMESTAMP))
   OR (l.end_date IS NULL AND m.__END_AT <= TIMESTAMP'{cutover}')
""")
extra = spark.sql(f"""
SELECT count(*) FROM {migrated} WHERE __START_AT <= TIMESTAMP'{cutover}'
""").first()[0] - spark.table(legacy).count()
results.append(("backfill matches the legacy table, keys included", mismatches.count() == 0 and extra == 0))
if mismatches.count():
    display(mismatches)

history_after_third = spark.sql(HISTORY_HASH).first()
results.append(("history not reloaded by the later updates", history_after_third == history_after_first))

missing = spark.sql(f"""
SELECT * FROM VALUES
  (103L, 'A1', 'Cid', TIMESTAMP'2025-01-15', TIMESTAMP'{refresh_60}'),
  ({new_key('A1', 'Pump', 'Ivy')}L, 'A1', 'Ivy', TIMESTAMP'{refresh_60}', TIMESTAMP'{refresh_75}'),
  (303L, 'A3', 'Eli', TIMESTAMP'2025-05-01', TIMESTAMP'{refresh_20}'),
  ({new_key('A3', 'Fan', 'Hal')}L, 'A3', 'Hal', TIMESTAMP'{refresh_20}', CAST(NULL AS TIMESTAMP)),
  (402L, 'A4', 'Gil', TIMESTAMP'2024-10-01', TIMESTAMP'{refresh_60}'),
  ({new_key('A5', 'Motor', 'Jo')}L, 'A5', 'Jo', TIMESTAMP'{refresh_60}', CAST(NULL AS TIMESTAMP))
  AS t(asset_sid, asset_id, asset_owner, start_at, end_at)
EXCEPT
SELECT asset_sid, asset_id, asset_owner, __START_AT, __END_AT FROM {migrated}
""")
results.append(("live versions: unchanged rows keep the open legacy key, new versions get new keys", missing.count() == 0))
if missing.count():
    display(missing)

reused = spark.sql(f"""
SELECT asset_sid, count(*) AS versions FROM {migrated} GROUP BY asset_sid HAVING count(*) > 1
""")
print("in the stored table (expected, step 85 fixes it): keys used by more than one version:", [tuple(r) for r in reused.collect()])

for name, ok in results:
    print("PASS" if ok else "FAIL", name)
assert all(ok for _, ok in results), "a check failed"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 85: the view with one key per version
# MAGIC
# MAGIC A plain view (1 table slot), created once after the first update: it needs the cut-over, the
# MAGIC last legacy date, which never changes after the migration.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {unique} AS
SELECT CASE WHEN __START_AT <= TIMESTAMP'{cutover}' THEN asset_sid
            ELSE xxhash64({ROW_HASH}, __START_AT) END AS asset_sid,
       asset_id, asset_name, asset_owner, __START_AT, __END_AT
FROM {migrated}
""")
spark.sql(f"ALTER VIEW {unique} SET TAGS ('design_pattern' = 'bronze_publish_scd2_autocdc_backfill_snapshot_sid_unique_sql')")
display(spark.sql(f"SELECT * FROM {unique} ORDER BY asset_id, __START_AT"))
duplicates = spark.sql(f"SELECT asset_sid FROM {unique} GROUP BY asset_sid HAVING count(*) > 1").count()
legacy_keys_kept = spark.sql(f"""
SELECT count(*) FROM {legacy} l JOIN {unique} k
  ON k.asset_sid = l.asset_sid AND k.__START_AT = CAST(l.start_date AS TIMESTAMP)
""").first()[0] == spark.table(legacy).count()
print("PASS" if duplicates == 0 else "FAIL", "one key per version in the view")
print("PASS" if legacy_keys_kept else "FAIL", "the view keeps every legacy key")
assert duplicates == 0 and legacy_keys_kept

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 90: remove everything (only when `teardown` is `true`)
# MAGIC
# MAGIC Deletes the pipeline, then drops the tables, the hidden `__materialization_mat_*` twins and
# MAGIC the event logs of this pipeline and of the view's own pipeline.

# COMMAND ----------

if teardown:
    view_pipeline = w.tables.get(source).pipeline_id
    pipeline_ids = [p.pipeline_id for p in w.pipelines.list_pipelines(filter=f"name LIKE '{pipeline_name}'")]
    for pid in pipeline_ids:
        w.pipelines.delete(pid)
    owners = [pid.replace("-", "_") for pid in pipeline_ids + [view_pipeline] if pid]
    spark.sql(f"DROP VIEW IF EXISTS {unique}")
    spark.sql(f"DROP MATERIALIZED VIEW IF EXISTS {source}")
    for name in ["asset_dim_migrated", "asset_source_base", "asset_dim_legacy"]:
        spark.sql(f"DROP TABLE IF EXISTS {target}.{name}")
    # information_schema, not the tables API: the API does not list twins or event logs.
    names = spark.sql(f"""
        SELECT table_name FROM {catalog}.information_schema.tables WHERE table_schema = '{schema}'
    """).collect()
    for (name,) in names:
        if any(name == f"event_log_{o}" or name.startswith(f"__materialization_mat_{o}_") for o in owners):
            spark.sql(f"DROP TABLE IF EXISTS {target}.`{name}`")
            print("dropped", name)
    w.workspace.delete(pipeline_folder, recursive=True)
    print("teardown done")
else:
    print("teardown skipped (set the widget to true)")
