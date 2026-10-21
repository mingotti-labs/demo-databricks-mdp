# Databricks notebook source
# Tags every table in pattern_bronze with its design pattern. The table is
# named after its pattern file, so the register ID is "bronze_" + table name.
# Idempotent; run after the pattern pipelines.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

from databricks.sdk import WorkspaceClient

OBJECT_TYPES = {
    "STREAMING_TABLE": "STREAMING TABLE",
    "MATERIALIZED_VIEW": "MATERIALIZED VIEW",
}

tables = list(WorkspaceClient().tables.list(catalog_name=catalog, schema_name="pattern_bronze"))
for t in tables:
    spark.sql(
        f"ALTER {OBJECT_TYPES[t.table_type.value]} `{catalog}`.`pattern_bronze`.`{t.name}` "
        f"SET TAGS ('design_pattern' = 'bronze_{t.name}')"
    )

dbutils.notebook.exit(f"Tagged {len(tables)} pattern tables")
