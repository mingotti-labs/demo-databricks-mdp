# Databricks notebook source
# Checks market_metrics_all_scd2's row count matches market_metrics_all_raw
# exactly -- proves the snapshot-based Auto CDC flow processed every
# (market, date) pair, keyed correctly, and that ingested_timestamp/
# transformed_timestamp are correctly excluded from history-triggering
# (otherwise this equality would fail after a second run).
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

raw_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_airroi.market_metrics_all_raw"
).collect()[0]["n"]
scd2_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_airroi_publish.market_metrics_all_scd2"
).collect()[0]["n"]

assert scd2_count == raw_count, (
    f"Row count mismatch: raw={raw_count} scd2={scd2_count}"
)

dbutils.notebook.exit(f"AirROI market_metrics_all_scd2 OK -- {raw_count} rows")
