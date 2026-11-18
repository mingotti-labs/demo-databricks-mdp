# Databricks notebook source
# MAGIC %md
# MAGIC # SCD2 migration with history, live source = append-only table (stream)
# MAGIC
# MAGIC Pattern `bronze_publish_scd2_autocdc_backfill_stream_sql`. Moves a legacy SCD type 2
# MAGIC dimension (`asset_dim_legacy`, with `start_date`/`end_date`) into a pipeline-owned SCD
# MAGIC type 2 table (`asset_dim_migrated`) **without a stage table**, then keeps it current from
# MAGIC an append-only table (`asset_source`) that has **no change timestamp**.
# MAGIC
# MAGIC Two Auto CDC flows write the target:
# MAGIC 1. **Backfill** (`AUTO CDC ONCE`): replays each legacy version as a change event at its
# MAGIC    `start_date` (plus a delete event at the `end_date` of a retired asset), so the legacy
# MAGIC    dates become `__START_AT`/`__END_AT`. It runs in the first update only; later updates
# MAGIC    leave it idle. `ONCE` still needs a streaming source, so the view streams the legacy table.
# MAGIC 2. **Live**: streams the change data feed of `asset_source`. The source has no timestamp,
# MAGIC    so each row is ordered by the time it was written (`_commit_timestamp`). Write at most one
# MAGIC    change per asset per write: two rows for one asset in one write share a commit time.
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
source = f"{target}.asset_source"
migrated = f"{target}.asset_dim_migrated"
pipeline_name = f"bronze--pattern--publish--scd2--backfill--stream--sql--{schema}"

notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
pipeline_folder = f"/Workspace{notebook_path.rsplit('/', 1)[0]}/transformations/{notebook_path.rsplit('/', 1)[1]}"
pipeline_file = f"{pipeline_folder}/asset_dim_migrated.sql"
print(target, pipeline_file, sep="\n")

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


def last_commit_time() -> str:
    """The commit time of the latest write to asset_source, from its change feed."""
    return spark.sql(f"SELECT max(_commit_timestamp) FROM table_changes('{source}', 0)").first()[0]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 10: the legacy SCD2 dimension

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {legacy} (
  asset_id STRING, asset_name STRING, asset_owner STRING, start_date DATE, end_date DATE
)
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 15: the live source, an append-only table without a timestamp
# MAGIC
# MAGIC One row per change, never updated or deleted, with the change data feed on so the
# MAGIC pipeline gets each row's commit time. A source that updates rows in place does not fit
# MAGIC this notebook: read it as a snapshot (the other notebook).

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {source} (asset_id STRING, asset_name STRING, asset_owner STRING)
TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 20: seed the live source (current state: A3 changed since the legacy table)

# COMMAND ----------

spark.sql(f"""
INSERT INTO {source} VALUES
  ('A1', 'Pump', 'Cid'),
  ('A3', 'Fan',  'Hal'),
  ('A4', 'Belt', 'Gil')
""")
commit_20 = last_commit_time()
print("written at", commit_20)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 25: seed the legacy history (A2 retired on 2025-03-01)

# COMMAND ----------

spark.sql(f"""
INSERT INTO {legacy} VALUES
  ('A1', 'Pump',  'Ann', DATE'2024-01-01', DATE'2024-06-01'),
  ('A1', 'Pump',  'Bob', DATE'2024-06-01', DATE'2025-01-15'),
  ('A1', 'Pump',  'Cid', DATE'2025-01-15', NULL),
  ('A2', 'Valve', 'Cy',  DATE'2024-02-01', DATE'2024-09-01'),
  ('A2', 'Valve', 'Dan', DATE'2024-09-01', DATE'2025-03-01'),
  ('A3', 'Fan',   'Di',  DATE'2024-03-01', DATE'2025-05-01'),
  ('A3', 'Fan',   'Eli', DATE'2025-05-01', NULL),
  ('A4', 'Belt',  'Flo', DATE'2024-04-01', DATE'2024-10-01'),
  ('A4', 'Belt',  'Gil', DATE'2024-10-01', NULL)
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 30: the pipeline file and its target
# MAGIC
# MAGIC The notebook writes `asset_dim_migrated.sql` into `transformations/<notebook name>/` next to
# MAGIC itself; the pipeline (step 55) reads that folder. Steps 40 and 50 add to the file.

# COMMAND ----------

def write_pipeline_file(text: str) -> None:
    w.workspace.mkdirs(pipeline_folder)
    w.workspace.upload(pipeline_file, io.BytesIO(text.encode()), format=ImportFormat.RAW, overwrite=True)


sql_target = """-- Written by the notebook bronze_publish_scd2_autocdc_backfill_stream_sql (step 30).
CREATE OR REFRESH STREAMING TABLE asset_dim_migrated;
"""
write_pipeline_file(sql_target)
print(sql_target)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 40: the backfill (`AUTO CDC ONCE` from `asset_history`)
# MAGIC
# MAGIC `asset_history` streams the legacy table and turns each version into a change event at its
# MAGIC `start_date`; the last version of a retired asset also gives a delete event at its `end_date`.
# MAGIC The last `start_date` per asset comes from a static lookup (a stream-static join).

# COMMAND ----------

sql_backfill = f"""
CREATE TEMPORARY VIEW asset_history AS
SELECT e.asset_id, e.asset_name, e.asset_owner, e.change_ts, e.is_delete
FROM (
  SELECT explode(
    CASE WHEN l.end_date IS NOT NULL AND l.start_date = last.last_start_date
      THEN array(
        named_struct('asset_id', l.asset_id, 'asset_name', l.asset_name, 'asset_owner', l.asset_owner,
                     'change_ts', CAST(l.start_date AS TIMESTAMP), 'is_delete', false),
        named_struct('asset_id', l.asset_id, 'asset_name', l.asset_name, 'asset_owner', l.asset_owner,
                     'change_ts', CAST(l.end_date AS TIMESTAMP), 'is_delete', true))
      ELSE array(
        named_struct('asset_id', l.asset_id, 'asset_name', l.asset_name, 'asset_owner', l.asset_owner,
                     'change_ts', CAST(l.start_date AS TIMESTAMP), 'is_delete', false))
    END) AS e
  FROM STREAM({legacy}) l
  JOIN (SELECT asset_id, max(start_date) AS last_start_date FROM {legacy} GROUP BY asset_id) last
    ON l.asset_id = last.asset_id
);

CREATE FLOW backfill_history AS AUTO CDC ONCE INTO asset_dim_migrated
FROM STREAM(asset_history)
KEYS (asset_id)
APPLY AS DELETE WHEN is_delete
SEQUENCE BY change_ts
COLUMNS * EXCEPT (is_delete, change_ts)
STORED AS SCD TYPE 2;
"""
write_pipeline_file(sql_target + sql_backfill)
print(sql_backfill)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 50: the live flow (streaming Auto CDC from `asset_live`)
# MAGIC
# MAGIC `asset_live` streams the change data feed of `asset_source`; `_commit_timestamp` is the
# MAGIC sequence. It is fixed, so a full refresh replays the changes in the same order.

# COMMAND ----------

sql_live = f"""
CREATE TEMPORARY VIEW asset_live AS
SELECT asset_id, asset_name, asset_owner, _commit_timestamp AS change_ts, false AS is_delete
FROM STREAM({source}) WITH (readChangeFeed = true)
WHERE _change_type = 'insert';

CREATE FLOW live_stream AS AUTO CDC INTO asset_dim_migrated
FROM STREAM(asset_live)
KEYS (asset_id)
APPLY AS DELETE WHEN is_delete
SEQUENCE BY change_ts
COLUMNS * EXCEPT (is_delete, change_ts)
STORED AS SCD TYPE 2;
"""
write_pipeline_file(sql_target + sql_backfill + sql_live)
print(sql_live)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 55: create (or reuse) the pipeline and run it
# MAGIC
# MAGIC Steps 10 to 25 recreate the tables, so a reused pipeline runs a full refresh: it resets both
# MAGIC flows and rebuilds `asset_dim_migrated`.

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
spark.sql(f"ALTER STREAMING TABLE {migrated} SET TAGS ('design_pattern' = 'bronze_publish_scd2_autocdc_backfill_stream_sql')")
cutover = spark.sql(f"""
SELECT max(d) FROM (SELECT start_date AS d FROM {legacy} UNION SELECT end_date FROM {legacy})
""").first()[0]

# The history part: rows started on a legacy date, with __END_AT only when a legacy date closed them.
HISTORY_HASH = f"""
SELECT count(*) AS n,
       sum(hash(asset_id, asset_name, asset_owner, __START_AT,
                CASE WHEN __END_AT <= TIMESTAMP'{cutover}' THEN __END_AT END)) AS h
FROM {migrated} WHERE __START_AT <= TIMESTAMP'{cutover}'
"""
history_after_first = spark.sql(HISTORY_HASH).first()
display(spark.sql(f"SELECT * FROM {migrated} ORDER BY asset_id, __START_AT"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 60: append new changes (A1 new owner, A5 new, A4 repeated unchanged)

# COMMAND ----------

spark.sql(f"""
INSERT INTO {source} VALUES
  ('A1', 'Pump',  'Ivy'),
  ('A4', 'Belt',  'Gil'),
  ('A5', 'Motor', 'Jo')
""")
commit_60 = last_commit_time()
print("written at", commit_60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 70: run the pipeline again

# COMMAND ----------

second_update = run_pipeline(pipeline_id)
display(spark.sql(f"SELECT * FROM {migrated} ORDER BY asset_id, __START_AT"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 80: checks

# COMMAND ----------

results = []

mismatches = spark.sql(f"""
SELECT l.*, m.__START_AT, m.__END_AT
FROM {legacy} l LEFT JOIN {migrated} m
  ON m.asset_id = l.asset_id AND m.asset_name = l.asset_name AND m.asset_owner = l.asset_owner
 AND m.__START_AT = CAST(l.start_date AS TIMESTAMP)
WHERE m.asset_id IS NULL
   OR (l.end_date IS NOT NULL AND NOT m.__END_AT <=> CAST(l.end_date AS TIMESTAMP))
   OR (l.end_date IS NULL AND m.__END_AT <= TIMESTAMP'{cutover}')
""")
extra = spark.sql(f"""
SELECT count(*) FROM {migrated} WHERE __START_AT <= TIMESTAMP'{cutover}'
""").first()[0] - spark.table(legacy).count()
results.append(("backfill matches the legacy table", mismatches.count() == 0 and extra == 0))
if mismatches.count():
    display(mismatches)

history_after_second = spark.sql(HISTORY_HASH).first()
backfill_ran_again = spark.sql(f"""
SELECT count(*) FROM event_log('{pipeline_id}')
WHERE event_type = 'flow_progress' AND origin.update_id = '{second_update}'
  AND origin.flow_name LIKE '%backfill_history' AND details:flow_progress.status = 'RUNNING'
""").first()[0]
results.append((
    "history not reloaded by the second update (backfill_history idle)",
    history_after_second == history_after_first and backfill_ran_again == 0,
))

missing = spark.sql(f"""
SELECT * FROM VALUES
  ('A1', 'Cid', TIMESTAMP'2025-01-15', TIMESTAMP'{commit_60}'),
  ('A1', 'Ivy', TIMESTAMP'{commit_60}', CAST(NULL AS TIMESTAMP)),
  ('A4', 'Gil', TIMESTAMP'2024-10-01', CAST(NULL AS TIMESTAMP)),
  ('A5', 'Jo',  TIMESTAMP'{commit_60}', CAST(NULL AS TIMESTAMP))
  AS t(asset_id, asset_owner, start_at, end_at)
EXCEPT
SELECT asset_id, asset_owner, __START_AT, __END_AT FROM {migrated}
""")
results.append(("step-60 changes applied at their commit time, unchanged row ignored", missing.count() == 0))
if missing.count():
    display(missing)

display(spark.sql(f"""
SELECT origin.update_id, origin.flow_name, details:flow_progress.status AS status, timestamp
FROM event_log('{pipeline_id}')
WHERE event_type = 'flow_progress' AND origin.update_id IN ('{first_update}', '{second_update}')
ORDER BY timestamp
"""))

for name, ok in results:
    print("PASS" if ok else "FAIL", name)
assert all(ok for _, ok in results), "a check failed"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 90: remove everything (only when `teardown` is `true`)
# MAGIC
# MAGIC Deletes the pipeline, then drops the tables, the hidden `__materialization_mat_*` twin and
# MAGIC the pipeline's event log.

# COMMAND ----------

if teardown:
    pipeline_ids = [p.pipeline_id for p in w.pipelines.list_pipelines(filter=f"name LIKE '{pipeline_name}'")]
    for pid in pipeline_ids:
        w.pipelines.delete(pid)
    owners = [pid.replace("-", "_") for pid in pipeline_ids]
    for name in ["asset_dim_migrated", "asset_source", "asset_dim_legacy"]:
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
