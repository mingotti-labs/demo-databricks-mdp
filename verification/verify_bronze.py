# Databricks notebook source
# MAGIC %md
# MAGIC # Verify bronze
# MAGIC Checks one source's bronze tables against `verification/bronze_checks/<source>.yml`:
# MAGIC the raw table landed real data, and the SCD tables hold every row that was not
# MAGIC quarantined. The rules are in `src/common/bronze_checks.py`.

# COMMAND ----------

import sys

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("source", "")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
workspace_file_path = dbutils.widgets.get("workspace_file_path")

sys.path.insert(0, f"{workspace_file_path}/src")
from common import bronze_checks  # noqa: E402

spec = bronze_checks.load_spec(
    f"{workspace_file_path}/verification/bronze_checks/{source}.yml"
)
raw_schema = f"{catalog}.{spec['raw_schema']}"
publish_schema = f"{catalog}.{spec['publish_schema']}"


def count(sql):
    return spark.sql(sql).collect()[0]["n"]


def current_rows(table):
    # SCD2 keeps closed versions, so only its current rows compare to raw
    return count(f"SELECT count(*) AS n FROM {publish_schema}.{table} WHERE __END_AT IS NULL")


# COMMAND ----------

# MAGIC %md
# MAGIC # Checks
# MAGIC One block per table in the spec. Every failure is collected, then asserted.

# COMMAND ----------

failures, summary = [], []
for table in spec["tables"]:
    raw = f"{raw_schema}.{table['raw']}"
    compared = bronze_checks.compared_rows(raw, table)
    counts = {
        "raw": count(f"SELECT count(*) AS n FROM {compared}"),
        "valid_distinct": count(bronze_checks.valid_distinct_keys_sql(compared, table["keys"], table.get("nullable_keys", []))),
    }
    if "scd2" in table:
        counts["scd2_current"] = current_rows(table["scd2"])
    if "scd1" in table:
        counts["scd1_current"] = count(f"SELECT count(*) AS n FROM {publish_schema}.{table['scd1']}")
    if "quarantine" in table:
        counts["quarantine"] = count(f"SELECT count(*) AS n FROM {raw_schema}.{table['quarantine']}")
    failures += bronze_checks.check_table(table, counts, set(spark.table(raw).columns))
    summary.append(f"{table['raw']}: raw={counts['raw']}, scd current={counts.get('scd2_current', counts.get('scd1_current'))}")

assert not failures, "; ".join(failures)

# COMMAND ----------

dbutils.notebook.exit(f"{source} bronze OK -- " + "; ".join(summary))
