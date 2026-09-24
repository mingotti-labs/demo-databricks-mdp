# Databricks notebook source
# Checks bronze_nsw_spatial.property_raw is populated with the expected
# shape -- proves the ArcGIS FeatureServer connector actually landed real
# data, not just that the pipeline ran without error.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

row_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_nsw_spatial.property_raw"
).collect()[0]["n"]
assert row_count > 0, "property_raw is empty"

columns = set(spark.table(f"{catalog}.bronze_nsw_spatial.property_raw").columns)
expected = {"propid", "addressstringoid", "address", "propertytype", "urbanity"}
assert expected.issubset(columns), f"missing expected columns: {expected - columns}"

dbutils.notebook.exit(f"property_raw ingestion OK -- {row_count} rows")
