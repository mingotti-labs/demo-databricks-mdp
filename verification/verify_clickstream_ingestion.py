# Databricks notebook source
# Checks bronze_clickstream.web_events_raw's row count matches the landing
# volume's file record count -- proves the Auto Loader pipeline actually
# landed everything, not just that it ran.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

LANDING_PATH = f"/Volumes/{catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing"

file_count = spark.read.json(LANDING_PATH).count()
table_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_clickstream.web_events_raw"
).collect()[0]["n"]

assert table_count == file_count, f"row count mismatch: files={file_count} table={table_count}"

dbutils.notebook.exit(f"bronze_clickstream ingestion OK -- {table_count} rows")
