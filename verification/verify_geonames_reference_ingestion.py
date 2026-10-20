# Databricks notebook source
# Checks bronze_geonames.{country_info,admin1_codes,admin2_codes,cities}_raw
# are populated with the expected shape -- proves the GeoNames dump-file
# pulls actually landed real data, not just that the pipeline ran without
# error.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

# GeoNames publishes a live dump that changes daily (admin2_codes went from
# 47,643 to 47,641 rows between two pulls), so reference counts are a band,
# not an equality: tight enough to catch a truncated or garbled pull.
TOLERANCE = 0.02
REFERENCE_COUNTS = {
    "country_info_raw": 252,
    "admin1_codes_raw": 3865,
    "admin2_codes_raw": 47643,
}

counts = {}
for table, reference in REFERENCE_COUNTS.items():
    count = spark.sql(
        f"SELECT count(*) AS n FROM {catalog}.bronze_geonames.{table}"
    ).collect()[0]["n"]
    assert abs(count - reference) <= reference * TOLERANCE, (
        f"{table}: {count} rows, more than {TOLERANCE:.0%} from the reference {reference}"
    )
    counts[table] = count
    columns = set(spark.table(f"{catalog}.bronze_geonames.{table}").columns)
    assert "ingested_timestamp" in columns, f"{table} is missing ingested_timestamp"

cities_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_geonames.cities_raw"
).collect()[0]["n"]
assert cities_count > 0, "cities_raw is empty"
cities_columns = set(spark.table(f"{catalog}.bronze_geonames.cities_raw").columns)
assert "ingested_timestamp" in cities_columns, (
    "cities_raw is missing ingested_timestamp"
)

dbutils.notebook.exit(
    "GeoNames ingestion OK -- "
    + ", ".join(f"{table}: {count} rows" for table, count in counts.items())
    + f", cities_raw: {cities_count} rows"
)
