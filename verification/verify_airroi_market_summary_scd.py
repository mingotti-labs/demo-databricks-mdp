# Databricks notebook source
# Checks market_summary_scd2's row count matches market_summary_raw
# exactly -- proves the snapshot-based Auto CDC flow actually processed
# every market, keyed correctly on the flat _country/_region/_locality
# columns (not the nested `market` map, which Auto CDC's keys= can't use).
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

raw_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_airroi.market_summary_raw"
).collect()[0]["n"]
scd2_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_airroi_publish.market_summary_scd2"
).collect()[0]["n"]

assert scd2_count == raw_count, (
    f"Row count mismatch: raw={raw_count} scd2={scd2_count}"
)

dbutils.notebook.exit(f"AirROI market_summary_scd2 OK -- {raw_count} rows")
