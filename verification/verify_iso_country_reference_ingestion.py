# Databricks notebook source
# Checks bronze_iso.country_codes_raw/subdivision_codes_raw are populated
# with the expected shape -- proves the ISO 3166 CSV pulls actually landed
# real data, not just that the pipeline ran without error.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

country_count = spark.sql(f"SELECT count(*) AS n FROM {catalog}.bronze_iso.country_codes_raw").collect()[
    0
]["n"]
assert country_count > 0, "country_codes_raw is empty"

country_columns = set(spark.table(f"{catalog}.bronze_iso.country_codes_raw").columns)
expected_country = {
    "country_code_alpha2",
    "country_code_alpha3",
    "numeric_code",
    "name_short",
    "name_long",
    "ingested_timestamp",
}
assert expected_country.issubset(
    country_columns
), f"missing expected columns: {expected_country - country_columns}"

subdivision_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_iso.subdivision_codes_raw"
).collect()[0]["n"]
assert subdivision_count > 0, "subdivision_codes_raw is empty"

subdivision_columns = set(spark.table(f"{catalog}.bronze_iso.subdivision_codes_raw").columns)
expected_subdivision = {
    "country_code_alpha2",
    "subdivision_code",
    "subdivision_name",
    "language_code",
    "ingested_timestamp",
}
assert expected_subdivision.issubset(
    subdivision_columns
), f"missing expected columns: {expected_subdivision - subdivision_columns}"
assert (
    "subdivision_code_iso3166-2" not in subdivision_columns
), "subdivision_code_iso3166-2 should have been renamed to subdivision_code"

# Quarantine + deduped must exactly partition subdivision_codes_raw -- see
# subdivision_codes_quarantine.py/subdivision_codes_deduped.py.
quarantine_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_iso.subdivision_codes_quarantine"
).collect()[0]["n"]
assert quarantine_count > 0, "subdivision_codes_quarantine is unexpectedly empty"

dbutils.notebook.exit(
    f"ISO 3166 ingestion OK -- country_codes_raw: {country_count} rows, "
    f"subdivision_codes_raw: {subdivision_count} rows, "
    f"subdivision_codes_quarantine: {quarantine_count} rows"
)
