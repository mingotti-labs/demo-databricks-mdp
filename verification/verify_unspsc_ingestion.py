# Databricks notebook source
# Checks bronze_ungm.unspsc_public_raw is populated with the expected shape
# -- proves the UNGM API pull actually landed real data, not just that the
# pipeline ran without error.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

row_count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_ungm.unspsc_public_raw").collect()[
    0
]["n"]
assert row_count > 0, "unspsc_public_raw is empty"

columns = set(spark.table(f"{catalog}.bronze_ungm.unspsc_public_raw").columns)
expected = {"Id", "ParentId", "UNSPSCode", "Title"}
assert expected.issubset(columns), f"missing expected columns: {expected - columns}"

dbutils.notebook.exit(f"unspsc_public_raw ingestion OK -- {row_count} rows")
