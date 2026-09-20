# Databricks notebook source
# Hand-rolled SCD Type 2 for Neon's customers table via the classic
# two-phase MERGE pattern -- the real SQL-native answer for a source
# that's already upsert-maintained (bronze_neon.customers_raw is merged in
# place by Lakeflow Connect, not appended to). AUTO CDC INTO only supports
# append-only streaming sources -- confirmed via a real
# DELTA_SOURCE_TABLE_IGNORE_CHANGES failure when this was first attempted
# as a streaming Auto CDC flow (see this job's OpenSpec design.md). MERGE
# isn't valid inside a declarative streaming-table/materialized-view body,
# so this can't be a Lakeflow Pipeline dataset -- it runs as a plain job
# instead. The MERGE statements below are the actual pattern; this
# notebook only exists to parameterize the catalog per target.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.bronze_neon_publish.customers_scd2_sql (
  id INT,
  first_name STRING,
  last_name STRING,
  email STRING,
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
MERGE INTO {catalog}.bronze_neon_publish.customers_scd2_sql AS target
USING {catalog}.bronze_neon.customers_raw AS source
ON target.id = source.id AND target.__END_AT IS NULL
WHEN MATCHED AND (
  target.first_name != source.first_name OR
  target.last_name != source.last_name OR
  target.email != source.email
) THEN UPDATE SET target.__END_AT = source.updated_at
""")

# COMMAND ----------

# Phase B: insert a new active version for any row that's brand new, or
# whose previous version was just expired above. Order matters -- this
# must run after Phase A, since it joins against the now-expired rows to
# find what still needs a fresh version.
spark.sql(f"""
MERGE INTO {catalog}.bronze_neon_publish.customers_scd2_sql AS target
USING (
  SELECT
    source.id, source.first_name, source.last_name, source.email,
    source.created_at, source.updated_at,
    source.updated_at AS __START_AT,
    CAST(NULL AS TIMESTAMP) AS __END_AT
  FROM {catalog}.bronze_neon.customers_raw AS source
  LEFT JOIN {catalog}.bronze_neon_publish.customers_scd2_sql AS current_version
    ON source.id = current_version.id AND current_version.__END_AT IS NULL
  WHERE current_version.id IS NULL
     OR source.first_name != current_version.first_name
     OR source.last_name != current_version.last_name
     OR source.email != current_version.email
) AS new_versions
ON target.id = new_versions.id AND target.__START_AT = new_versions.__START_AT
WHEN NOT MATCHED THEN INSERT *
""")

dbutils.notebook.exit("customers_scd2_sql merge complete")
