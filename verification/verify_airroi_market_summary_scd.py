# Databricks notebook source
# Checks market_summary_scd2's row count matches market_summary_raw
# exactly -- proves the snapshot-based Auto CDC flow actually processed
# every market, keyed correctly on the flat _country/_region/_locality/
# _district columns (not the nested `market` map, which Auto CDC's keys=
# can't use). Also proves ingested_timestamp/transformed_timestamp are
# correctly excluded from history-triggering -- if they weren't, this
# equality would fail after a second run (spurious extra versions).
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
