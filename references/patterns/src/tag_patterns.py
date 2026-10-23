# Databricks notebook source
# Tags every table in pattern_bronze and pattern_bronze_publish with its design
# pattern. A pattern_bronze table is named after its pattern file, so the register
# ID is "bronze_" + table name; a pattern_bronze_publish table is named by the ID.
# Idempotent; run after the pattern pipelines.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

from databricks.sdk import WorkspaceClient

OBJECT_TYPES = {
    "STREAMING_TABLE": "STREAMING TABLE",
    "MATERIALIZED_VIEW": "MATERIALIZED VIEW",
    "MANAGED": "TABLE",
}
SCHEMAS = {"pattern_bronze": "bronze_", "pattern_bronze_publish": ""}

client = WorkspaceClient()
tagged = 0
for schema, prefix in SCHEMAS.items():
    for t in client.tables.list(catalog_name=catalog, schema_name=schema):
        if t.name.startswith(("event_log_", "__materialization_")):
            continue
        spark.sql(
            f"ALTER {OBJECT_TYPES[t.table_type.value]} `{catalog}`.`{schema}`.`{t.name}` "
            f"SET TAGS ('design_pattern' = '{prefix}{t.name}')"
        )
        tagged += 1

dbutils.notebook.exit(f"Tagged {tagged} pattern tables")
