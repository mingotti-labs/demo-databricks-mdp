# Databricks notebook source
# Dev only (openspec dev-runs-as-service-principal): attach tables left behind
# by a deleted human-owned dev pipeline to the CI/CD SP's pipeline, so the SP
# keeps their rows, SCD2 history and Auto Loader checkpoints without a reload.
# Deployed by CI, so it runs as the SP, the owner of the destination pipeline,
# which the move requires. Reads each table's pipeline from Unity Catalog (SHOW
# TBLPROPERTIES is stale for a materialized view after a move). A table already
# on the destination is skipped, so the job can be rerun.
from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("pipeline_id", "")
dbutils.widgets.text("tables", "")
catalog = dbutils.widgets.get("catalog")
pipeline_id = dbutils.widgets.get("pipeline_id")
tables = [t.strip() for t in dbutils.widgets.get("tables").split(",") if t.strip()]

client = WorkspaceClient()
print("running as", client.current_user.me().user_name)

# COMMAND ----------

KINDS = {"STREAMING_TABLE": "STREAMING TABLE", "MATERIALIZED_VIEW": "MATERIALIZED VIEW"}


def move(name: str) -> str:
    table = client.tables.get(f"{catalog}.{name}")
    if table.pipeline_id == pipeline_id:
        return "already there"
    spark.sql(
        f"ALTER {KINDS[table.table_type.value]} {catalog}.{name} "
        f"SET TBLPROPERTIES ('pipelines.pipelineId' = '{pipeline_id}')"
    )
    moved = client.tables.get(f"{catalog}.{name}")
    if moved.pipeline_id != pipeline_id:
        raise RuntimeError(f"still on pipeline {moved.pipeline_id}")
    return f"moved from {table.pipeline_id}, owner {moved.owner}"


results, failures = {}, {}
for name in tables:
    try:
        results[name] = move(name)
    except Exception as error:  # noqa: BLE001 - report every table, fail at the end
        failures[name] = f"{type(error).__name__}: {error}"
for name, outcome in {**results, **failures}.items():
    print(f"{name}: {outcome}")
if failures:
    raise RuntimeError(f"{len(failures)} of {len(tables)} tables not moved: {failures}")
dbutils.notebook.exit(f"{len(results)} tables on pipeline {pipeline_id}")
