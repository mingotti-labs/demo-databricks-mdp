# Databricks notebook source
# Checks every Silver Landing table against its selected Bronze Publish
# source: row count parity, non-null source_name/transformed_timestamp,
# and (for SCD2-sourced entities) is_current correctly derived from
# scd_valid_to_timestamp. See docs/medallion/silver.md and
# openspec/changes/phase4a-silver-landing/design.md for the full contract.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

ENTITIES = [
    {"source": "neon", "table": "customers", "bronze_schema": "bronze_neon_publish", "bronze_table": "customers_scd2", "scd2": True},
    {"source": "neon", "table": "products", "bronze_schema": "bronze_neon_publish", "bronze_table": "products_scd2", "scd2": True},
    {"source": "neon", "table": "orders", "bronze_schema": "bronze_neon_publish", "bronze_table": "orders_scd1", "scd2": False},
    {"source": "neon", "table": "order_items", "bronze_schema": "bronze_neon_publish", "bronze_table": "order_items_scd1", "scd2": False},
    {"source": "clickstream", "table": "web_events", "bronze_schema": "bronze_clickstream_publish", "bronze_table": "web_events_scd1", "scd2": False},
    {"source": "ungm", "table": "unspsc_public", "bronze_schema": "bronze_ungm_publish", "bronze_table": "unspsc_public_scd2", "scd2": True},
    {"source": "acnc", "table": "charity_register", "bronze_schema": "bronze_acnc_publish", "bronze_table": "charity_register_scd2", "scd2": True},
    {"source": "nsw_spatial", "table": "property", "bronze_schema": "bronze_nsw_spatial_publish", "bronze_table": "property_scd2", "scd2": True},
    {"source": "airroi", "table": "market_metrics_all", "bronze_schema": "bronze_airroi_publish", "bronze_table": "market_metrics_all_scd2", "scd2": True},
    {"source": "airroi", "table": "market_summary", "bronze_schema": "bronze_airroi_publish", "bronze_table": "market_summary_scd2", "scd2": True},
    {"source": "iso", "table": "country_codes", "bronze_schema": "bronze_iso_publish", "bronze_table": "country_codes_scd2", "scd2": True},
    {"source": "iso", "table": "subdivision_codes", "bronze_schema": "bronze_iso_publish", "bronze_table": "subdivision_codes_scd2", "scd2": True},
    {"source": "geonames", "table": "country_info", "bronze_schema": "bronze_geonames_publish", "bronze_table": "country_info_scd2", "scd2": True},
    {"source": "geonames", "table": "admin1_codes", "bronze_schema": "bronze_geonames_publish", "bronze_table": "admin1_codes_scd2", "scd2": True},
    {"source": "geonames", "table": "admin2_codes", "bronze_schema": "bronze_geonames_publish", "bronze_table": "admin2_codes_scd2", "scd2": True},
    {"source": "geonames", "table": "cities", "bronze_schema": "bronze_geonames_publish", "bronze_table": "cities_scd2", "scd2": True},
]

# Sources whose Bronze Publish SCD2 objects carry ingested_timestamp
# (stamped at their own _raw layer) -- Silver Landing propagates it
# unchanged, never stamps or overwrites it.
SOURCES_WITH_INGESTED_TIMESTAMP = {"airroi", "iso", "geonames"}


def count(fqn: str, where: str = "1=1") -> int:
    return spark.sql(f"SELECT count(*) AS n FROM {fqn} WHERE {where}").collect()[0]["n"]


failures = []

for entity in ENTITIES:
    silver_fqn = f"{catalog}.silver_landing_{entity['source']}.{entity['table']}"
    bronze_fqn = f"{catalog}.{entity['bronze_schema']}.{entity['bronze_table']}"
    label = f"{entity['source']}.{entity['table']}"

    silver_count = count(silver_fqn)
    bronze_count = count(bronze_fqn)
    if silver_count != bronze_count:
        failures.append(f"{label}: row count mismatch (silver={silver_count} bronze={bronze_count})")

    bad_provenance = count(silver_fqn, "source_name IS NULL OR transformed_timestamp IS NULL")
    if bad_provenance:
        failures.append(f"{label}: {bad_provenance} rows with null source_name/transformed_timestamp")

    if entity["scd2"]:
        bad_is_current = count(
            silver_fqn,
            "is_current != (scd_valid_to_timestamp IS NULL)",
        )
        if bad_is_current:
            failures.append(f"{label}: {bad_is_current} rows with is_current not matching scd_valid_to_timestamp")

    if entity["source"] in SOURCES_WITH_INGESTED_TIMESTAMP:
        null_ingested = count(silver_fqn, "ingested_timestamp IS NULL")
        if null_ingested:
            failures.append(
                f"{label}: {null_ingested} rows with null ingested_timestamp "
                f"(expected non-null for {entity['source']})"
            )

assert not failures, "Silver Landing verification failed:\n" + "\n".join(failures)

dbutils.notebook.exit(f"Silver Landing OK -- {len(ENTITIES)} entities verified")
