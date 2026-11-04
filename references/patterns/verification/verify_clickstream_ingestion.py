# Databricks notebook source
# Checks pattern_bronze.autoloader_add_new_columns_python's row count matches the landing
# volume's file record count -- proves the Auto Loader pipeline actually
# landed everything, not just that it ran.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

LANDING_PATH = f"/Volumes/{catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing"

file_count = spark.read.json(LANDING_PATH).count()
table_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.pattern_bronze.autoloader_add_new_columns_python"
).collect()[0]["n"]

assert table_count == file_count, f"row count mismatch: files={file_count} table={table_count}"

dbutils.notebook.exit(f"pattern_bronze autoloader_add_new_columns_python ingestion OK -- {table_count} rows")
