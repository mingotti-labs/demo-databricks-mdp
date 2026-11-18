# Databricks notebook source
# MAGIC %md
# MAGIC # SCD2 migration with history, live source = materialized view (snapshot)
# MAGIC
# MAGIC Pattern `bronze_publish_scd2_autocdc_backfill_snapshot_sql`. Moves a legacy SCD type 2
# MAGIC dimension (`asset_dim_legacy`, with `start_date`/`end_date`) into a pipeline-owned SCD
# MAGIC type 2 table (`asset_dim_migrated`) **without a stage table**, then keeps it current from
# MAGIC a materialized view (`asset_source`) that has **no change timestamp**.
# MAGIC
# MAGIC One Auto CDC snapshot flow `WITH VERSION` does both jobs:
# MAGIC 1. **Backfill**: one snapshot per distinct legacy date, in order. Each legacy
# MAGIC    `start_date`/`end_date` becomes `__START_AT`/`__END_AT`.
# MAGIC 2. **Live**: one snapshot per refresh of the view; the version is the view's refresh time
# MAGIC    (`information_schema.tables.last_altered`).
# MAGIC
# MAGIC Why one flow: a table fed by a snapshot flow accepts no other flow
# MAGIC (`MULTI_QUERY_SNAPSHOT_TARGET_NOT_SUPPORTED`), so a separate once-only backfill flow is not
# MAGIC possible here. The history is read once: after the first update the saved version is past
# MAGIC every legacy date, and versions only move forward.
# MAGIC
# MAGIC **Cost of the first update**: one full comparison per distinct legacy date (about 20 seconds
# MAGIC each on Free Edition). Count the dates first (step 25 prints them).
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
pipeline_name = f"bronze--pattern--publish--scd2--backfill--snapshot--sql--{schema}"

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


def last_altered(table: str) -> str:
    """The refresh time of a materialized view, as information_schema reports it."""
    return spark.sql(f"""
        SELECT last_altered FROM {catalog}.information_schema.tables
        WHERE table_schema = '{schema}' AND table_name = '{table}'
    """).first()[0]

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
# MAGIC ## Step 15: the live source, a materialized view without a timestamp
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
print("view refreshed at", last_altered("asset_source"))

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


sql_target = """-- Written by the notebook bronze_publish_scd2_autocdc_backfill_snapshot_sql (step 30).
CREATE OR REFRESH STREAMING TABLE asset_dim_migrated;
"""
write_pipeline_file(sql_target)
print(sql_target)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 40: the views
# MAGIC
# MAGIC - `asset_history`: each legacy version with the dates it was valid.
# MAGIC - `asset_live`: the materialized view (current state).
# MAGIC - `asset_union`: both; the flow picks one part per version.
# MAGIC - `asset_versions`: every version to process: each legacy date, then the view's refresh time.
# MAGIC - `asset_cutover`: the last legacy date.

# COMMAND ----------

sql_views = f"""
CREATE TEMPORARY VIEW asset_history AS
SELECT asset_id, asset_name, asset_owner,
       CAST(start_date AS TIMESTAMP) AS valid_from, CAST(end_date AS TIMESTAMP) AS valid_to
FROM {legacy};

CREATE TEMPORARY VIEW asset_live AS
SELECT asset_id, asset_name, asset_owner FROM {source};

CREATE TEMPORARY VIEW asset_union AS
SELECT asset_id, asset_name, asset_owner, valid_from, valid_to, false AS is_live FROM asset_history
UNION ALL
SELECT asset_id, asset_name, asset_owner, CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP), true
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
# MAGIC `WITH VERSION` returns the next version after the last one processed, or no row when
# MAGIC nothing is new. `FROM SNAPSHOT` returns the rows for that version: the legacy rows valid on
# MAGIC that date, or the view after the last legacy date. `current_snapshot_version()` must be
# MAGIC called in plain subqueries; inside a `WITH` clause it is not resolved.

# COMMAND ----------

sql_flow = """
CREATE FLOW migrate_and_load AS AUTO CDC INTO asset_dim_migrated
FROM SNAPSHOT (
  SELECT u.asset_id, u.asset_name, u.asset_owner
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
results.append(("history not reloaded by the second update", history_after_second == history_after_first))

missing = spark.sql(f"""
SELECT * FROM VALUES
  ('A1', 'Cid', TIMESTAMP'2025-01-15', TIMESTAMP'{refresh_60}'),
  ('A1', 'Ivy', TIMESTAMP'{refresh_60}', CAST(NULL AS TIMESTAMP)),
  ('A4', 'Gil', TIMESTAMP'2024-10-01', TIMESTAMP'{refresh_60}'),
  ('A5', 'Jo',  TIMESTAMP'{refresh_60}', CAST(NULL AS TIMESTAMP))
  AS t(asset_id, asset_owner, start_at, end_at)
EXCEPT
SELECT asset_id, asset_owner, __START_AT, __END_AT FROM {migrated}
""")
results.append(("step-60 changes applied at the view's refresh time", missing.count() == 0))
if missing.count():
    display(missing)

display(spark.sql(f"""
SELECT origin.update_id, details:flow_progress.status AS status, timestamp
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
# MAGIC Deletes the pipeline, then drops the tables, the hidden `__materialization_mat_*` twins and
# MAGIC the event logs of this pipeline and of the view's own pipeline.

# COMMAND ----------

if teardown:
    view_pipeline = w.tables.get(source).pipeline_id
    pipeline_ids = [p.pipeline_id for p in w.pipelines.list_pipelines(filter=f"name LIKE '{pipeline_name}'")]
    for pid in pipeline_ids:
        w.pipelines.delete(pid)
    owners = [pid.replace("-", "_") for pid in pipeline_ids + [view_pipeline] if pid]
    spark.sql(f"DROP MATERIALIZED VIEW IF EXISTS {source}")
    for name in ["asset_dim_migrated", "asset_source_base", "asset_dim_legacy"]:
        spark.sql(f"DROP TABLE IF EXISTS {target}.{name}")
    for t in w.tables.list(catalog_name=catalog, schema_name=schema):
        if any(t.name in (f"event_log_{o}",) or t.name.startswith(f"__materialization_mat_{o}_") for o in owners):
            spark.sql(f"DROP TABLE IF EXISTS {target}.`{t.name}`")
            print("dropped", t.name)
    w.workspace.delete(pipeline_folder, recursive=True)
    print("teardown done")
else:
    print("teardown skipped (set the widget to true)")
