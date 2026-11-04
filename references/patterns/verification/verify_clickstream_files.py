# Databricks notebook source
# Checks the clickstream landing volume has files with actual event records --
# proves the seed job wrote real data, not just empty files.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

LANDING_PATH = f"/Volumes/{catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing"

files = [f for f in dbutils.fs.ls(LANDING_PATH) if f.name.endswith(".json")]
assert len(files) > 0, "no batch files found in the landing path"

# COMMAND ----------

record_count = spark.read.json(LANDING_PATH).count()
assert record_count > 0, "landing path files contain no records"

dbutils.notebook.exit(f"clickstream files OK -- {len(files)} files, {record_count} records")
