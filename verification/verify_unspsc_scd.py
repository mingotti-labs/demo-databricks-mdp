# Databricks notebook source
# Checks unspsc_public_scd1/scd2 row counts match unspsc_public_raw exactly
# -- proves the snapshot-based Auto CDC flows actually processed every row,
# not just that the pipeline ran.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

raw_count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_ungm.unspsc_public_raw").collect()[
    0
]["n"]

mismatches = []
for table in ["unspsc_public_scd1", "unspsc_public_scd2"]:
    count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_ungm_publish.{table}").collect()[0][
        "n"
    ]
    if count != raw_count:
        mismatches.append(f"{table}: raw={raw_count} scd={count}")

assert not mismatches, "Row count mismatch: " + "; ".join(mismatches)

dbutils.notebook.exit(f"unspsc SCD1/SCD2 OK -- {raw_count} rows each")
