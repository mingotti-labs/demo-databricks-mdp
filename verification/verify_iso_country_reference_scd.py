# Databricks notebook source
# Checks country_codes_scd2/subdivision_codes_scd2 -- proves the
# snapshot-based Auto CDC flows processed every row, not just that the
# pipeline ran. SCD2-only for this source (no SCD1 tables) -- current-row
# count (`__END_AT IS NULL`) is what's compared, not total row count, since
# a rerun with no source changes should never create spurious history.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

country_raw_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_iso.country_codes_raw"
).collect()[0]["n"]
country_current_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_iso_publish.country_codes_scd2 WHERE __END_AT IS NULL"
).collect()[0]["n"]
assert (
    country_current_count == country_raw_count
), f"country_codes_scd2 current-row count {country_current_count} != raw count {country_raw_count}"

# subdivision_codes_raw has genuine duplicate rows on the SCD key
# (subdivision_code, language_code, subdivision_name) -- confirmed via a
# real run (DUPLICATE_KEY_VIOLATION) and fixed with a deduplicating private
# view upstream of Auto CDC. The current-row count should match the
# *distinct* key count, not the raw row count -- see
# subdivision_codes_deduped.py.
subdivision_raw_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_iso.subdivision_codes_raw"
).collect()[0]["n"]
subdivision_quarantine_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_iso.subdivision_codes_quarantine"
).collect()[0]["n"]
subdivision_distinct_key_count = spark.sql(
    f"""
    SELECT count(*) AS n FROM (
        SELECT DISTINCT subdivision_code, language_code, subdivision_name
        FROM {catalog}.bronze_iso.subdivision_codes_raw
    )
    """
).collect()[0]["n"]
assert subdivision_raw_count == subdivision_distinct_key_count + subdivision_quarantine_count, (
    f"raw ({subdivision_raw_count}) != deduped ({subdivision_distinct_key_count}) + "
    f"quarantine ({subdivision_quarantine_count}) -- every raw row should land somewhere"
)

subdivision_current_count = spark.sql(
    f"SELECT count(*) AS n FROM {catalog}.bronze_iso_publish.subdivision_codes_scd2 WHERE __END_AT IS NULL"
).collect()[0]["n"]
assert subdivision_current_count == subdivision_distinct_key_count, (
    f"subdivision_codes_scd2 current-row count {subdivision_current_count} != "
    f"distinct key count {subdivision_distinct_key_count}"
)

dbutils.notebook.exit(
    f"ISO 3166 SCD2 OK -- country_codes_scd2: {country_current_count} current rows, "
    f"subdivision_codes_scd2: {subdivision_current_count} current rows"
)
