# Databricks notebook source
# Checks bronze_neon row counts match the Neon source exactly -- proves the
# ingestion pipeline actually landed everything, not just that it ran.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

import psycopg2

conn = psycopg2.connect(
    host=dbutils.secrets.get("neon-postgres", "host"),
    dbname=dbutils.secrets.get("neon-postgres", "database_name"),
    user=dbutils.secrets.get("neon-postgres", "role_name"),
    password=dbutils.secrets.get("neon-postgres", "password"),
    sslmode="require",
)
cur = conn.cursor()

tables = ["customers", "products", "orders", "order_items"]
neon_counts = {}
for table in tables:
    cur.execute(f"SELECT count(*) FROM {table}")
    neon_counts[table] = cur.fetchone()[0]
cur.close()
conn.close()

# COMMAND ----------

mismatches = []
bronze_counts = {}
for table in tables:
    bronze_table = f"{table}_raw"
    bronze_counts[table] = spark.sql(
        f"SELECT count(*) AS n FROM {catalog}.bronze_neon.{bronze_table}"
    ).collect()[0]["n"]
    if bronze_counts[table] != neon_counts[table]:
        mismatches.append(f"{table}: neon={neon_counts[table]} bronze={bronze_counts[table]}")

assert not mismatches, "Row count mismatch: " + "; ".join(mismatches)

dbutils.notebook.exit(f"bronze_neon ingestion OK -- {bronze_counts}")
