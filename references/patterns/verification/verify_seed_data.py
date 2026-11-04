# Databricks notebook source
# Checks the Neon dev branch's seed data: non-empty tables and referential
# integrity. Connects directly (not via the UC Connection) -- same path the seed
# job itself uses.
import psycopg2

conn = psycopg2.connect(
    host=dbutils.secrets.get("neon-postgres", "host"),
    dbname=dbutils.secrets.get("neon-postgres", "database_name"),
    user=dbutils.secrets.get("neon-postgres", "role_name"),
    password=dbutils.secrets.get("neon-postgres", "password"),
    sslmode="require",
)
cur = conn.cursor()

# COMMAND ----------

counts = {}
for table in ["customers", "products", "orders", "order_items"]:
    cur.execute(f"SELECT count(*) FROM {table}")
    counts[table] = cur.fetchone()[0]
    assert counts[table] > 0, f"{table} is empty"

# COMMAND ----------

cur.execute(
    "SELECT count(*) FROM orders o LEFT JOIN customers c ON o.customer_id = c.id "
    "WHERE c.id IS NULL"
)
orphan_orders = cur.fetchone()[0]
assert orphan_orders == 0, f"{orphan_orders} orders reference a missing customer"

cur.execute(
    "SELECT count(*) FROM order_items oi "
    "LEFT JOIN orders o ON oi.order_id = o.id "
    "LEFT JOIN products p ON oi.product_id = p.id "
    "WHERE o.id IS NULL OR p.id IS NULL"
)
orphan_items = cur.fetchone()[0]
assert orphan_items == 0, f"{orphan_items} order_items reference a missing order or product"

cur.close()
conn.close()

dbutils.notebook.exit(f"seed data OK -- {counts}, referential integrity holds")
