# Databricks notebook source
# Hand-rolled SCD Type 2 for Neon's products table -- see
# customers_scd2_merge.py for the full write-up on why this pattern exists
# and why it can't be a Lakeflow Pipeline dataset.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.bronze_neon_publish.products_scd2_sql (
  id INT,
  name STRING,
  category STRING,
  price DECIMAL(10, 2),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  __START_AT TIMESTAMP,
  __END_AT TIMESTAMP
) USING DELTA
""")

# COMMAND ----------

# Phase A: expire the currently-active version of any row whose tracked
# columns changed since the last run.
spark.sql(f"""
MERGE INTO {catalog}.bronze_neon_publish.products_scd2_sql AS target
USING {catalog}.bronze_neon.products_raw AS source
ON target.id = source.id AND target.__END_AT IS NULL
WHEN MATCHED AND (
  target.name != source.name OR
  target.category != source.category OR
  target.price != source.price
) THEN UPDATE SET target.__END_AT = source.updated_at
""")

# COMMAND ----------

# Phase B: insert a new active version for any row that's brand new, or
# whose previous version was just expired above.
spark.sql(f"""
MERGE INTO {catalog}.bronze_neon_publish.products_scd2_sql AS target
USING (
  SELECT
    source.id, source.name, source.category, source.price,
    source.created_at, source.updated_at,
    source.updated_at AS __START_AT,
    CAST(NULL AS TIMESTAMP) AS __END_AT
  FROM {catalog}.bronze_neon.products_raw AS source
  LEFT JOIN {catalog}.bronze_neon_publish.products_scd2_sql AS current_version
    ON source.id = current_version.id AND current_version.__END_AT IS NULL
  WHERE current_version.id IS NULL
     OR source.name != current_version.name
     OR source.category != current_version.category
     OR source.price != current_version.price
) AS new_versions
ON target.id = new_versions.id AND target.__START_AT = new_versions.__START_AT
WHEN NOT MATCHED THEN INSERT *
""")

dbutils.notebook.exit("products_scd2_sql merge complete")
