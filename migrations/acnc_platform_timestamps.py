# Databricks notebook source
# One-off migration for openspec correct-platform-timestamps: acnc's SCD2,
# Landing and Normalised tables were pipeline-owned and are rebuilt by a job
# or a streaming flow now. Acts only on the old table types, so it is a
# no-op once applied. The SCD2 backup is kept until it is dropped by hand.
from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")
client = WorkspaceClient()
done = []


def table_type(name):
    return (
        client.tables.get(name).table_type.value
        if spark.catalog.tableExists(name)
        else None
    )


def count(name):
    return spark.table(name).count()


# COMMAND ----------

scd2 = f"{catalog}.bronze_acnc_publish.charity_register_scd2"
backup = f"{scd2}_backup"
if table_type(scd2) == "STREAMING_TABLE":
    if not spark.catalog.tableExists(backup):
        spark.sql(f"CREATE TABLE {backup} AS SELECT * FROM {scd2}")
    assert count(backup) == count(scd2), "backup row count differs"
    spark.sql(f"DROP TABLE {scd2}")
    spark.sql(f"""
CREATE TABLE {scd2}
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true', 'delta.enableRowTracking' = 'true')
AS SELECT * EXCEPT (ingested_timestamp, transformed_timestamp),
  __START_AT AS ingested_timestamp,
  coalesce(__END_AT, __START_AT) AS transformed_timestamp
FROM {backup}
""")
    assert count(scd2) == count(backup), "recreated row count differs"
    done.append(f"scd2 recreated ({count(scd2)} rows)")

# COMMAND ----------

landing = f"{catalog}.silver_landing_acnc.charity_register"
if table_type(landing) == "MATERIALIZED_VIEW":
    spark.sql(f"DROP MATERIALIZED VIEW {landing}")
    done.append("landing dropped")

for t in client.tables.list(catalog_name=catalog, schema_name="silver_normalised_acnc"):
    if t.table_type.value == "MATERIALIZED_VIEW":
        spark.sql(f"DROP MATERIALIZED VIEW {t.full_name}")
        done.append(f"dropped {t.name}")

dbutils.notebook.exit("; ".join(done) or "nothing to migrate")
