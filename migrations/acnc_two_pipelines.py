# Databricks notebook source
# One-off migration for openspec change acnc-two-pipelines (design D3, D4).
# Moves the three tables of acnc's SCD and Landing pipelines into the
# pipelines that will own them (bronze ingestion, Silver Normalised) with
# Databricks' table move, then deletes the two emptied pipelines so the
# consolidation PR can deploy without a destructive-action prompt.
#
# Must run as the owner and run-as of all four pipelines: the CI/CD service
# principal, i.e. trigger this job by id, never as a notebook. Idempotent: a
# table already owned by its destination is skipped, an already-deleted
# pipeline is not stopped or deleted again. Row and closed-version counts
# are checked unchanged before anything is deleted.
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

dbutils.widgets.text("catalog", "")
for name in ("ingestion_id", "scd_id", "landing_id", "normalised_id"):
    dbutils.widgets.text(name, "")
catalog = dbutils.widgets.get("catalog")
ids = {
    n: dbutils.widgets.get(n)
    for n in ("ingestion_id", "scd_id", "landing_id", "normalised_id")
}

MOVES = [
    (
        "STREAMING TABLE",
        "bronze_acnc_publish.charity_register_scd1",
        ids["scd_id"],
        ids["ingestion_id"],
    ),
    (
        "STREAMING TABLE",
        "bronze_acnc_publish.charity_register_scd2",
        ids["scd_id"],
        ids["ingestion_id"],
    ),
    (
        "MATERIALIZED VIEW",
        "silver_landing_acnc.charity_register",
        ids["landing_id"],
        ids["normalised_id"],
    ),
]
EMPTIED = (ids["scd_id"], ids["landing_id"])
w = WorkspaceClient()


def owner(table: str) -> str:
    """Return the id of the pipeline that owns a table."""
    rows = spark.sql(
        f"SHOW TBLPROPERTIES {catalog}.{table} ('pipelines.pipelineId')"
    ).collect()
    return rows[0]["value"]


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


before = {table: counts(table) for _, table, _, _ in MOVES}

for pipeline_id in EMPTIED:
    if exists(pipeline_id):
        w.pipelines.stop_and_wait(pipeline_id)

for kind, table, source, destination in MOVES:
    if owner(table) == destination:
        print(f"{table}: already owned by {destination}")
        continue
    assert owner(table) == source, (
        f"{table}: owned by {owner(table)}, expected {source}"
    )
    spark.sql(
        f"ALTER {kind} {catalog}.{table} SET TBLPROPERTIES('pipelines.pipelineId'='{destination}')"
    )
    print(f"{table}: moved {source} -> {destination}")

problems = [
    f"{table}: owner {owner(table)} != {destination}"
    for _, table, _, destination in MOVES
    if owner(table) != destination
] + [
    f"{table}: counts {before[table]} -> {counts(table)}"
    for _, table, _, _ in MOVES
    if counts(table) != before[table]
]
assert not problems, "Migration check failed, nothing deleted: " + "; ".join(problems)

for pipeline_id in EMPTIED:
    if exists(pipeline_id):
        w.pipelines.delete(pipeline_id)
        print(f"deleted emptied pipeline {pipeline_id}")

dbutils.notebook.exit(
    "acnc-two-pipelines migration OK -- "
    + "; ".join(f"{t} rows/closed {before[t]}" for _, t, _, _ in MOVES)
)
