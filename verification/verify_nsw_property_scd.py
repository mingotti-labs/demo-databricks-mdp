# Databricks notebook source
# Checks property_scd1/scd2 row counts match property_raw exactly, and
# that addressstringoid is actually unique in property_raw -- proves the
# key correction (addressstringoid, not propid) holds on the current data,
# not just that the pipeline ran.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

raw_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_nsw_spatial.property_raw"
).collect()[0]["n"]
distinct_key_count = spark.sql(
    f"SELECT count(DISTINCT addressstringoid) AS n FROM {catalog}.bronze_nsw_spatial.property_raw"
).collect()[0]["n"]
assert distinct_key_count == raw_count, (
    f"addressstringoid is not unique in property_raw: {distinct_key_count} distinct "
    f"of {raw_count} rows"
)

mismatches = []
for table in ["property_scd1", "property_scd2"]:
    count = spark.sql(
        f"SELECT count(*) AS n FROM {catalog}.bronze_nsw_spatial_publish.{table}"
    ).collect()[0]["n"]
    if count != raw_count:
        mismatches.append(f"{table}: raw={raw_count} scd={count}")

assert not mismatches, "Row count mismatch: " + "; ".join(mismatches)

dbutils.notebook.exit(f"NSW property SCD1/SCD2 OK -- {raw_count} rows each")
