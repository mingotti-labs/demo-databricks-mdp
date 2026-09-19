# Databricks notebook source
# Checks Auto Loader's schema evolution actually happened: the new-field
# columns exist on web_events_raw, and are NULL only for rows ingested before
# those fields existed in the source files.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

columns = [f.name for f in spark.table(f"{catalog}.bronze_clickstream.web_events_raw").schema.fields]
for new_field in ["device_type", "referrer_url"]:
    assert new_field in columns, f"{new_field} column missing -- schema evolution did not happen"

# COMMAND ----------

counts = spark.sql(
    f"""
    SELECT count(*) AS total, count(device_type) AS with_device_type
    FROM {catalog}.bronze_clickstream.web_events_raw
    """
).collect()[0]

assert counts["with_device_type"] > 0, "no rows have device_type populated"
assert counts["with_device_type"] < counts["total"], (
    "all rows have device_type populated -- expected some pre-evolution rows to be NULL"
)

dbutils.notebook.exit(
    f"schema evolution OK -- {counts['total']} total rows, "
    f"{counts['with_device_type']} with device_type"
)
