# Databricks notebook source
# Checks {country_info,admin1_codes,admin2_codes,cities}_scd2's
# current-row count (`__END_AT IS NULL`) matches its `_raw` counterpart's
# row count exactly -- proves the snapshot-based Auto CDC flows processed
# every row, not just that the pipeline ran. All four keys were confirmed
# unique against the real source data before implementation (unlike ISO's
# subdivision_code), so no quarantine table exists for any GeoNames table.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

TABLES = ["country_info", "admin1_codes", "admin2_codes", "cities"]

mismatches = []
counts = {}
for table in TABLES:
    raw_count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_geonames.{table}_raw").collect()[
        0
    ]["n"]
    current_count = spark.sql(
        f"SELECT count(*) AS n FROM {catalog}.bronze_geonames_publish.{table}_scd2 WHERE __END_AT IS NULL"
    ).collect()[0]["n"]
    counts[table] = current_count
    if current_count != raw_count:
        mismatches.append(f"{table}: raw={raw_count} scd2_current={current_count}")

assert not mismatches, "Row count mismatch: " + "; ".join(mismatches)

dbutils.notebook.exit(
    "GeoNames SCD2 OK -- "
    + ", ".join(f"{table}_scd2: {count} current rows" for table, count in counts.items())
)
