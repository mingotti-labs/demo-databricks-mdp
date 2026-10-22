# Databricks notebook source
# Applies the Silver Normalised Unity Catalog tags to every table of one
# source's normalised spec. A separate step because @dp.materialized_view
# has no tags parameter; ALTER ... SET TAGS on pipeline datasets is GA.
# Idempotent, run after every refresh by the silver--{source} job.
import sys

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("source", "")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
workspace_file_path = dbutils.widgets.get("workspace_file_path")

sys.path.insert(0, f"{workspace_file_path}/src")
from databricks.sdk import WorkspaceClient  # noqa: E402

from common.design_patterns import OBJECT_TYPES  # noqa: E402
from common.normalised_spec import load_spec, tables  # noqa: E402

spec = load_spec(
    f"{workspace_file_path}/src/layers/silver/normalised/specs/{source}.yml"
)

# COMMAND ----------

client = WorkspaceClient()
for table, kind in tables(spec).items():
    name = f"{catalog}.silver_normalised_{source}.{table}"
    object_type = OBJECT_TYPES[client.tables.get(name).table_type.value]
    tags = {"mdp_layer": "silver_normalised", "mdp_source_system": source}
    if kind:
        tags["mdp_entity_kind"] = kind
    pairs = ", ".join(f"'{k}' = '{v}'" for k, v in tags.items())
    spark.sql(
        f"ALTER {object_type} `{catalog}`.`silver_normalised_{source}`.`{table}` SET TAGS ({pairs})"
    )

dbutils.notebook.exit(
    f"Tagged {len(tables(spec))} tables in silver_normalised_{source}"
)
