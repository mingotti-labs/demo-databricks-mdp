# Databricks notebook source
# Rebuilds every Silver Normalised table of one source in full, keeping
# transformed_timestamp on rows that did not change (common/keep_timestamps.py,
# openspec correct-platform-timestamps, probe P3). A job task, not a pipeline:
# a materialized view cannot read its own previous result.
import sys

for name in ("catalog", "source", "workspace_file_path"):
    dbutils.widgets.text(name, "")
catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
workspace_file_path = dbutils.widgets.get("workspace_file_path")

sys.path.insert(0, f"{workspace_file_path}/src")
from common.keep_timestamps import keep_timestamps  # noqa: E402
from common.normalised_spec import load_spec  # noqa: E402
from layers.silver.normalised import transforms as sn  # noqa: E402

spark.sql(f"USE CATALOG `{catalog}`")
spec = load_spec(f"{workspace_file_path}/src/layers/silver/normalised/specs/{source}.yml")

# COMMAND ----------

for name, build in sn.builders(spark, spec).items():
    table = f"silver_normalised_{source}.{name}"
    previous = spark.table(table) if spark.catalog.tableExists(table) else None
    (
        keep_timestamps(build(), previous)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table)
    )

dbutils.notebook.exit(f"Rebuilt silver_normalised_{source}")
