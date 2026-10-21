# Databricks notebook source
# Tags every table of one source with its design pattern. A separate step
# because pipeline decorators have no tags parameter; ALTER ... SET TAGS on
# pipeline datasets is GA. Idempotent, run after the last pipeline of each
# run_{source} job.
import sys

from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("source", "")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
workspace_file_path = dbutils.widgets.get("workspace_file_path")

sys.path.insert(0, f"{workspace_file_path}/src")
from common.design_patterns import (  # noqa: E402
    OBJECT_TYPES,
    TAG,
    load_mapping,
    pattern_for,
)

entry = load_mapping(f"{workspace_file_path}/src/common/design_patterns.yml")[source]

# COMMAND ----------

client = WorkspaceClient()
count = 0
for schema in entry["schemas"]:
    for t in client.tables.list(catalog_name=catalog, schema_name=schema):
        pattern = pattern_for(entry, schema, t.name)
        spark.sql(
            f"ALTER {OBJECT_TYPES[t.table_type.value]} `{catalog}`.`{schema}`.`{t.name}` "
            f"SET TAGS ('{TAG}' = '{pattern}')"
        )
        count += 1

dbutils.notebook.exit(f"Tagged {count} tables for {source}")
