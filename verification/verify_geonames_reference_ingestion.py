# Databricks notebook source
# Checks bronze_geonames.{country_info,admin1_codes,admin2_codes,cities}_raw
# are populated with the expected shape -- proves the GeoNames dump-file
# pulls actually landed real data, not just that the pipeline ran without
# error.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

EXPECTED_COUNTS = {
    "country_info_raw": 252,
    "admin1_codes_raw": 3865,
    "admin2_codes_raw": 47643,
}

for table, expected_count in EXPECTED_COUNTS.items():
    count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_geonames.{table}").collect()[0]["n"]
    assert count == expected_count, f"{table}: expected {expected_count} rows, found {count}"
    columns = set(spark.table(f"{catalog}.bronze_geonames.{table}").columns)
    assert "ingested_timestamp" in columns, f"{table} is missing ingested_timestamp"

cities_count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_geonames.cities_raw").collect()[0][
    "n"
]
assert cities_count > 0, "cities_raw is empty"
cities_columns = set(spark.table(f"{catalog}.bronze_geonames.cities_raw").columns)
assert "ingested_timestamp" in cities_columns, "cities_raw is missing ingested_timestamp"

dbutils.notebook.exit(
    f"GeoNames ingestion OK -- country_info_raw: {EXPECTED_COUNTS['country_info_raw']} rows, "
    f"admin1_codes_raw: {EXPECTED_COUNTS['admin1_codes_raw']} rows, "
    f"admin2_codes_raw: {EXPECTED_COUNTS['admin2_codes_raw']} rows, "
    f"cities_raw: {cities_count} rows"
)
