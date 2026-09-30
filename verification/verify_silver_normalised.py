# Databricks notebook source
# Checks one source's Silver Normalised tables against its normalised spec
# and its Silver Landing tables: drift, parity, key uniqueness, bridge
# element counts, value completeness, FK integrity, lineage totals, match
# keys, tags, timestamps and tolerances. Collects every failure, then
# asserts. Contract: docs/medallion/silver.md ("Silver Normalised").
import re
import sys

from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("source", "")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
workspace_file_path = dbutils.widgets.get("workspace_file_path")

sys.path.insert(0, f"{workspace_file_path}/src")
from common import normalised_spec as ns  # noqa: E402
from common.silver_normalised import landing_rows  # noqa: E402

spec = ns.load_spec(
    f"{workspace_file_path}/src/layers/silver/normalised/specs/{source}.yml"
)
schema = f"silver_normalised_{source}"
spark.sql(f"USE CATALOG `{catalog}`")
failures: list[str] = []


def table(name: str):
    return spark.read.table(f"`{catalog}`.`{schema}`.`{name}`")


def duplicates(df, keys: list[str]) -> int:
    return df.groupBy(*keys).count().where("count > 1").count()


# COMMAND ----------

# Drift: every Landing column used, ignored or a platform column.
landing_tables = {ns.landing_table(e["from"]) for e in spec["base_entities"].values()}
landing_columns = {
    t: [c.name for c in spark.read.table(f"silver_landing_{source}.{t}").schema]
    for t in landing_tables
}
failures += ns.drift(spec, landing_columns)

# COMMAND ----------

# Base entities: parity with Landing (plus quarantine) and key uniqueness.
quarantine = {t["entity"] for t in spec.get("dependency_tolerance", [])}
for name, entity in spec["base_entities"].items():
    landing = spark.read.table(entity["from"]).count()
    built = table(name).count() + (
        table(f"{name}_quarantine").count() if name in quarantine else 0
    )
    if built != landing:
        failures.append(f"{name}: {built} rows (+ quarantine) vs {landing} in Landing")
    keys = list(entity["natural_key"]) + (
        ["scd_valid_from_timestamp"] if entity.get("history") == "scd2" else []
    )
    if n := duplicates(table(name), keys):
        failures.append(f"{name}: {n} duplicate natural keys")

# COMMAND ----------

# Bridges: element count matches Landing.
for name, entity in spec.get("bridge_entities", {}).items():
    rows = landing_rows(spark, spec, entity["parent"])
    if "explode" in entity:
        column, split = entity["explode"]["column"], entity["explode"]["split"]
        expected = (
            rows.where(F.col(column).isNotNull())
            .select(F.sum(F.size(F.split(F.col(column), re.escape(split)))))
            .first()[0]
            or 0
        )
    else:
        pattern = ns.like_to_regex(entity["unpivot"]["columns_like"])
        keep = entity["unpivot"]["keep_when"]
        flags = [c for c in rows.columns if pattern.fullmatch(c)]
        expected = sum(
            rows.where(F.col(c).cast("string") == keep).count() for c in flags
        )
    if (actual := table(name).count()) != expected:
        failures.append(
            f"{name}: {actual} bridge rows vs {expected} elements in Landing"
        )

# COMMAND ----------

# Extracted entities: completeness, uniqueness, FK integrity, match keys, lineage.
lineage = table("value_lineage")
for name, entity in spec.get("extracted_entities", {}).items():
    values = table(name)
    for kind, owner, column in ns.members(spec)[name]:
        source_df = landing_rows(spark, spec, owner) if kind == "base" else table(owner)
        missing = (
            source_df.where(F.col(column).isNotNull())
            .select(F.col(column).alias("v"))
            .distinct()
            .join(values, F.col("v") == F.col(name), "left_anti")
            .count()
        )
        if missing:
            failures.append(f"{name}: {missing} values of {owner}.{column} missing")
    if n := duplicates(values, [name]):
        failures.append(
            f"{name}: {n} values with more than one row (a dependency no longer holds)"
        )
    if parent := entity.get("parent"):
        orphans = (
            values.where(F.col(parent).isNotNull())
            .join(
                table(parent).select(F.col(parent).alias("p")),
                F.col(parent) == F.col("p"),
                "left_anti",
            )
            .count()
        )
        if orphans:
            failures.append(
                f"{name}: {orphans} rows whose parent {parent} does not exist"
            )
    if n := values.where("rdm_proposed_match_key IS NULL").count():
        failures.append(f"{name}: {n} rows with null rdm_proposed_match_key")
    totals = (
        lineage.where(F.col("entity") == name)
        .groupBy("value")
        .agg(F.sum("row_count").alias("lineage_rows"))
    )
    mismatched = (
        values.select(F.col(name).cast("string").alias("value"), "row_count")
        .join(totals, "value", "full_outer")
        .where("row_count IS NULL OR lineage_rows IS NULL OR row_count != lineage_rows")
        .count()
    )
    if mismatched:
        failures.append(
            f"{name}: {mismatched} values whose row_count differs from value_lineage"
        )

# COMMAND ----------

# Tags and timestamps on every table.
expected_tables = ns.tables(spec)
tags = {
    (r.table_name, r.tag_name): r.tag_value
    for r in spark.sql(
        f"SELECT table_name, tag_name, tag_value FROM `{catalog}`.information_schema.table_tags "
        f"WHERE schema_name = '{schema}'"
    ).collect()
}
for name, kind in expected_tables.items():
    wanted = {"mdp.layer": "silver_normalised", "mdp.source_system": source}
    if kind:
        wanted["mdp.entity_kind"] = kind
    for tag, value in wanted.items():
        if tags.get((name, tag)) != value:
            failures.append(
                f"{name}: tag {tag} is {tags.get((name, tag))!r}, expected {value!r}"
            )
    nulls = (
        table(name)
        .where("ingested_timestamp IS NULL OR transformed_timestamp IS NULL")
        .count()
    )
    if nulls:
        failures.append(
            f"{name}: {nulls} rows with null ingested_timestamp/transformed_timestamp"
        )

# COMMAND ----------

# Tolerances: violating determinant values within the declared limit.
for t in spec.get("dependency_tolerance", []):
    violating = (
        spark.read.table(spec["base_entities"][t["entity"]]["from"])
        .where(F.col(t["determinant"]).isNotNull())
        .groupBy(t["determinant"])
        .agg(F.countDistinct(t["dependent"]).alias("n"))
        .where("n > 1")
        .count()
    )
    if violating > t["max_violations"]:
        failures.append(
            f"{t['entity']}: {violating} violating {t['determinant']} values, max {t['max_violations']}"
        )

assert not failures, (
    f"Silver Normalised verification failed for {source}:\n" + "\n".join(failures)
)

dbutils.notebook.exit(
    f"Silver Normalised OK -- {source}, {len(expected_tables)} tables verified"
)
