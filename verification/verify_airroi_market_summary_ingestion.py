# Databricks notebook source
# Checks bronze_airroi.market_summary_raw is populated with the expected
# shape -- proves the AirROI fetch helper actually landed real data for
# all four markets, not just that the pipeline ran without error.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

row_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_airroi.market_summary_raw"
).collect()[0]["n"]
assert row_count == 4, f"expected exactly 4 markets, found {row_count}"

columns = set(spark.table(f"{catalog}.bronze_airroi.market_summary_raw").columns)
expected = {
    "_country",
    "_region",
    "_locality",
    "_district",
    "active_listings_count",
    "average_daily_rate",
    "occupancy",
    "rev_par",
    "revenue",
    "ingested_timestamp",
}
assert expected.issubset(columns), f"missing expected columns: {expected - columns}"

dbutils.notebook.exit(f"market_summary_raw ingestion OK -- {row_count} markets")
