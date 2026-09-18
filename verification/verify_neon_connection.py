# Databricks notebook source
# Checks the neon_dev UC Connection is actually live, not just present. A bare
# Connection isn't independently browsable -- SHOW SCHEMAS IN CONNECTION is not
# valid syntax (confirmed the hard way) -- so this uses the real mechanism: a
# temporary foreign catalog, browsed, then dropped.
CATALOG = "neon_dev_verification_tmp"

spark.sql(
    f"CREATE FOREIGN CATALOG IF NOT EXISTS {CATALOG} "
    "USING CONNECTION neon_dev OPTIONS (database 'app')"
)
try:
    schemas = [r["databaseName"] for r in spark.sql(f"SHOW SCHEMAS IN {CATALOG}").collect()]
    assert "public" in schemas, f"Expected 'public' schema in neon_dev, got {schemas}"
finally:
    spark.sql(f"DROP CATALOG IF EXISTS {CATALOG}")

dbutils.notebook.exit(f"neon_dev connection OK -- schemas: {schemas}")
