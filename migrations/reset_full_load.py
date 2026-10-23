# Databricks notebook source
# One-off per source for openspec rollout-bronze-full-pattern: Silver Landing
# was a materialized view and is now a streaming table over the SCD2 change
# feed, and a materialized view cannot become a streaming table in place. Drops
# the old Landing tables, plus any SCD2 tables listed in `also_drop` (a new
# load). Acts only while the first Landing table is still a materialized view,
# so it is a no-op once applied.
from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("landing", "")
dbutils.widgets.text("also_drop", "")
catalog = dbutils.widgets.get("catalog")
landing = [t for t in dbutils.widgets.get("landing").split(",") if t]
also_drop = [t for t in dbutils.widgets.get("also_drop").split(",") if t]

client = WorkspaceClient()


def table_type(name):
    return client.tables.get(f"{catalog}.{name}").table_type.value


def drop(name):
    if not spark.catalog.tableExists(f"{catalog}.{name}"):
        return False
    kind = "MATERIALIZED VIEW" if table_type(name) == "MATERIALIZED_VIEW" else "TABLE"
    spark.sql(f"DROP {kind} {catalog}.{name}")
    return True


# COMMAND ----------

pending = (
    spark.catalog.tableExists(f"{catalog}.{landing[0]}")
    and table_type(landing[0]) == "MATERIALIZED_VIEW"
)
dropped = [name for name in (landing + also_drop) if pending and drop(name)]

dbutils.notebook.exit(
    f"dropped: {', '.join(dropped)}" if dropped else "nothing to reset"
)
