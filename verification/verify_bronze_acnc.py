# Databricks notebook source
# MAGIC %md
# MAGIC # Verify bronze: ACNC Charity Register
# MAGIC Checks the raw table landed real data, then that the SCD tables hold
# MAGIC every row that was not quarantined.

# COMMAND ----------

dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

# MAGIC %md
# MAGIC # Ingestion
# MAGIC `charity_register_raw` is populated and has the expected columns: proves the
# MAGIC CKAN connector actually landed real data, not just that the pipeline ran
# MAGIC without error.

# COMMAND ----------

raw_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_acnc.charity_register_raw"
).collect()[0]["n"]
assert raw_count > 0, "charity_register_raw is empty"

columns = set(spark.table(f"{catalog}.bronze_acnc.charity_register_raw").columns)
expected = {"ABN", "Charity_Legal_Name", "State", "Registration_Date"}
assert expected.issubset(columns), f"missing expected columns: {expected - columns}"

# COMMAND ----------

# MAGIC %md
# MAGIC # SCD tables
# MAGIC `charity_register_scd1` and the current rows of `charity_register_scd2` equal
# MAGIC raw minus `charity_register_quarantine` (NULL-ABN charities, excluded from SCD
# MAGIC tracking): proves the snapshot Auto CDC flows processed every non-quarantined
# MAGIC row, and that quarantine accounts for the rest.

# COMMAND ----------

quarantine_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_acnc.charity_register_quarantine"
).collect()[0]["n"]
expected_count = raw_count - quarantine_count

mismatches = []
# scd2 keeps closed historical versions, so only its current rows compare to raw
for table, current_only in [
    ("charity_register_scd1", ""),
    ("charity_register_scd2", " WHERE __END_AT IS NULL"),
]:
    count = spark.sql(
        f"SELECT count(*) AS n FROM {catalog}.bronze_acnc_publish.{table}{current_only}"
    ).collect()[0]["n"]
    if count != expected_count:
        mismatches.append(f"{table}: expected={expected_count} actual={count}")

assert not mismatches, "Row count mismatch: " + "; ".join(mismatches)

# COMMAND ----------

dbutils.notebook.exit(
    f"charity_register bronze OK -- raw={raw_count}, quarantined={quarantine_count}, "
    f"SCD1/SCD2 current={expected_count} each"
)
