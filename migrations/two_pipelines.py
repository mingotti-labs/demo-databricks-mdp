# Databricks notebook source
# Moves tables from a source's SCD pipeline into its bronze ingestion
# pipeline with Databricks' table move, then deletes the emptied SCD
# pipeline, so the consolidation PR can deploy without a destructive-action
# prompt (openspec ungm-iso-geonames-nsw-two-pipelines D2; procedure and
# evidence: archived acnc-two-pipelines design.md, NAMING.md "Removing a
# pipeline").
#
# Must run as the owner and run-as of both pipelines: the CI/CD service
# principal, i.e. trigger the job by id, never from a notebook session.
# Idempotent: a table already owned by the destination is skipped, an
# already-deleted source pipeline is not stopped or deleted again. Owner is
# read from Unity Catalog, not SHOW TBLPROPERTIES (stale after a move for a
# materialized view). Row and closed-version counts are checked unchanged
# before the source pipeline is deleted.
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

for name in ("catalog", "source_pipeline_id", "destination_pipeline_id", "tables"):
    dbutils.widgets.text(name, "")
catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source_pipeline_id")
destination = dbutils.widgets.get("destination_pipeline_id")
tables = [t.strip() for t in dbutils.widgets.get("tables").split(",") if t.strip()]
w = WorkspaceClient()


def uc_table(table: str):
    """Return the Unity Catalog metadata of a table."""
    return w.tables.get(f"{catalog}.{table}")


def owner(table: str) -> str:
    """Return the id of the pipeline that owns a table."""
    return uc_table(table).properties["pipelines.pipelineId"]


def kind(table: str) -> str:
    """Return the ALTER keyword for a table: STREAMING TABLE or MATERIALIZED VIEW."""
    return uc_table(table).table_type.value.replace("_", " ")


def counts(table: str) -> tuple[int, int]:
    """Return (rows, closed SCD2 versions); closed is 0 for non-SCD2 tables."""
    columns = spark.table(f"{catalog}.{table}").columns
    closed = "count_if(__END_AT IS NOT NULL)" if "__END_AT" in columns else "0"
    row = spark.sql(
        f"SELECT count(*) AS n, {closed} AS c FROM {catalog}.{table}"
    ).collect()[0]
    return row["n"], row["c"]


def exists(pipeline_id: str) -> bool:
    """Return whether a pipeline still exists."""
    try:
        w.pipelines.get(pipeline_id)
        return True
    except NotFound:
        return False


before = {table: counts(table) for table in tables}

if exists(source):
    w.pipelines.stop_and_wait(source)

for table in tables:
    if owner(table) == destination:
        print(f"{table}: already owned by {destination}")
        continue
    assert owner(table) == source, (
        f"{table}: owned by {owner(table)}, expected {source}"
    )
    spark.sql(
        f"ALTER {kind(table)} {catalog}.{table} "
        f"SET TBLPROPERTIES('pipelines.pipelineId'='{destination}')"
    )
    print(f"{table}: moved {source} -> {destination}")

problems = [
    f"{table}: owner {owner(table)} != {destination}"
    for table in tables
    if owner(table) != destination
] + [
    f"{table}: counts {before[table]} -> {counts(table)}"
    for table in tables
    if counts(table) != before[table]
]
assert not problems, "Migration check failed, nothing deleted: " + "; ".join(problems)

if exists(source):
    w.pipelines.delete(source)
    print(f"deleted emptied pipeline {source}")

dbutils.notebook.exit(
    "two-pipelines migration OK -- "
    + "; ".join(f"{t} rows/closed {before[t]}" for t in tables)
)
