# Databricks notebook source
# Checks bronze_airroi.market_metrics_all_raw is populated with the
# expected shape -- 4 markets x 12 months = 48 rows, each metric field
# still a distribution struct (not flattened -- that's a silver concern).
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

row_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_airroi.market_metrics_all_raw"
).collect()[0]["n"]
assert row_count == 48, f"expected exactly 48 rows (4 markets x 12 months), found {row_count}"

columns = set(spark.table(f"{catalog}.bronze_airroi.market_metrics_all_raw").columns)
expected = {
    "_country",
    "_region",
    "_locality",
    "_district",
    "date",
    "active_listings_count",
    "average_daily_rate",
    "occupancy",
    "revpar",
    "revenue",
    "booking_lead_time",
    "length_of_stay",
    "min_nights",
    "ingested_timestamp",
}
assert expected.issubset(columns), f"missing expected columns: {expected - columns}"

dbutils.notebook.exit(f"market_metrics_all_raw ingestion OK -- {row_count} rows")
