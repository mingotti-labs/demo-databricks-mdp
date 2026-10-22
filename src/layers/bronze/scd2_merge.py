# Databricks notebook source
# Applies one source's current snapshot to its SCD2 table, writing only the
# rows that changed (common/scd2_merge.py). A job task, not a pipeline
# dataset: MERGE is not valid inside a pipeline, and snapshot Auto CDC
# rewrites every current row on every run (openspec
# correct-platform-timestamps, probe P2).
import sys

for name in ("catalog", "source", "where", "target", "keys", "workspace_file_path"):
    dbutils.widgets.text(name, "")
catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
where = dbutils.widgets.get("where")
target = dbutils.widgets.get("target")
keys = dbutils.widgets.get("keys").split(",")

sys.path.insert(0, f"{dbutils.widgets.get('workspace_file_path')}/src")
from common.scd2_merge import merge_sql  # noqa: E402

spark.sql(f"USE CATALOG `{catalog}`")

# COMMAND ----------

if not spark.catalog.tableExists(target):
    spark.sql(f"""
CREATE TABLE {target}
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true', 'delta.enableRowTracking' = 'true')
AS SELECT *, CAST(NULL AS TIMESTAMP) AS transformed_timestamp,
  CAST(NULL AS TIMESTAMP) AS __START_AT, CAST(NULL AS TIMESTAMP) AS __END_AT
FROM {source} WHERE false
""")

snapshot = f"(SELECT * FROM {source} WHERE {where})" if where else source
result = spark.sql(merge_sql(target, snapshot, keys, spark.table(source).columns)).first()
dbutils.notebook.exit(
    f"{target}: {result['num_inserted_rows']} inserted, {result['num_updated_rows']} closed"
)
