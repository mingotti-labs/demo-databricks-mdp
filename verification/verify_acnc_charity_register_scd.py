# Databricks notebook source
# Checks charity_register_scd1/scd2 row counts match charity_register_raw
# minus charity_register_quarantine exactly -- proves the snapshot-based
# Auto CDC flows processed every non-quarantined row, and that quarantine
# accounts for the rest (NULL-ABN charities excluded from SCD tracking).
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

raw_count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_acnc.charity_register_raw").collect()[
    0
]["n"]
quarantine_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_acnc.charity_register_quarantine"
).collect()[0]["n"]
expected_count = raw_count - quarantine_count

mismatches = []
for table in ["charity_register_scd1", "charity_register_scd2"]:
    count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_acnc_publish.{table}").collect()[0][
        "n"
    ]
    if count != expected_count:
        mismatches.append(f"{table}: expected={expected_count} actual={count}")

assert not mismatches, "Row count mismatch: " + "; ".join(mismatches)

dbutils.notebook.exit(
    f"charity_register SCD1/SCD2 OK -- {expected_count} rows each "
    f"(raw={raw_count}, quarantined={quarantine_count})"
)
