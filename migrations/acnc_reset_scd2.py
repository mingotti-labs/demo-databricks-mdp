# Databricks notebook source
# One-off for openspec correct-platform-timestamps (new load, no migration):
# acnc's SCD2 table was a plain Delta table written by a MERGE task. The bronze
# pipeline owns it again, so drop it with its backup and Silver Landing (whose
# stream read the old table's change feed); both pipelines rebuild them from
# one load. Acts only while the SCD2 table is not pipeline-owned, so it is a
# no-op once applied.
from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")
scd2 = f"{catalog}.bronze_acnc_publish.charity_register_scd2"
tables = [
    scd2,
    f"{scd2}_backup",
    f"{catalog}.silver_landing_acnc.charity_register",
]

client = WorkspaceClient()
is_plain = (
    spark.catalog.tableExists(scd2)
    and client.tables.get(scd2).table_type.value == "MANAGED"
)
dropped = []
if is_plain:
    for name in tables:
        spark.sql(f"DROP TABLE IF EXISTS {name}")
        dropped.append(name)

dbutils.notebook.exit(f"dropped: {', '.join(dropped)}" if dropped else "nothing to reset")
