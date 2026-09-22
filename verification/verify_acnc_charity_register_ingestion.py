# Databricks notebook source
# Checks bronze_acnc.charity_register_raw is populated with the expected
# shape -- proves the CKAN connector actually landed real data, not just
# that the pipeline ran without error.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

row_count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_acnc.charity_register_raw").collect()[
    0
]["n"]
assert row_count > 0, "charity_register_raw is empty"

columns = set(spark.table(f"{catalog}.bronze_acnc.charity_register_raw").columns)
expected = {"ABN", "Charity_Legal_Name", "State", "Registration_Date"}
assert expected.issubset(columns), f"missing expected columns: {expected - columns}"

dbutils.notebook.exit(f"charity_register_raw ingestion OK -- {row_count} rows")
