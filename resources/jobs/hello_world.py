# Databricks notebook source
# CI/CD smoke test for demo-databricks-mdp. Not part of any data layer -- proves a
# bundle-deployed job runs on serverless compute with the CI/CD identity's permissions
# against this target's catalog.
dbutils.widgets.text("catalog", "")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

print(f"Hello, world -- demo-databricks-mdp CI/CD smoke test, target catalog: {catalog}")

# COMMAND ----------

spark.sql(f"USE CATALOG `{catalog}`")
result = spark.sql("SELECT current_catalog() AS catalog").collect()[0]["catalog"]
print(f"Confirmed active catalog: {result}")
