# Spark transforms of the generic Silver Normalised pipeline: one function
# per table kind, each returning the DataFrame for one materialized view of
# a source's normalised spec. Rules and column layout:
# docs/medallion/silver.md ("Silver Normalised") and
# openspec phase4d-silver-normalised-framework's design.md.
import re
from functools import reduce

from pyspark import cloudpickle
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from common import normalised_spec as ns
from common.normalised_spec import (
    VALIDITY_COLUMNS,
    bridge_attribute,
    landing_table,
    parent_column,
)

# UDFs run in worker processes that lack the driver's sys.path entry for
# src/, so a by-reference pickle of ns.match_key fails to import there.
# By-value pickling ships the tested function itself.
cloudpickle.register_pickle_by_value(ns)
match_key_udf = F.udf(ns.match_key, "string")

NATURAL_KEY_COMMENT = {"comment": "Natural key"}


def _stamped(df: DataFrame) -> DataFrame:
    return df.withColumn("transformed_timestamp", F.current_timestamp())


def landing_rows(
    spark: SparkSession, spec: dict, name: str, quarantined: bool = False
) -> DataFrame:
    """A base entity's Landing rows, without (or only) its quarantined rows.

    A row is quarantined when its determinant value violates one of the
    entity's dependency tolerances. Joins, not set operations: Spark set
    operations reject MAP columns.
    """
    landing = spark.read.table(spec["base_entities"][name]["from"])
    if "ingested_timestamp" not in landing.columns:
        raise ValueError(
            f"{name}: Landing lacks ingested_timestamp (Silver Normalised precondition)"
        )
    columns, excepted = landing.columns, F.lit(False)
    tolerances = [
        t for t in spec.get("dependency_tolerance", []) if t["entity"] == name
    ]
    for i, t in enumerate(tolerances):
        marker = f"_violating_{i}"
        bad = (
            landing.where(F.col(t["determinant"]).isNotNull())
            .groupBy(t["determinant"])
            .agg(F.countDistinct(t["dependent"]).alias("n"))
            .where("n > 1")
            .select(F.col(t["determinant"]).alias(marker))
        )
        landing = landing.join(bad, F.col(t["determinant"]) == F.col(marker), "left")
        excepted = excepted | F.col(marker).isNotNull()
    return landing.where(excepted if quarantined else ~excepted).select(*columns)


def _key_columns(base: dict) -> list[str]:
    return list(base["natural_key"]) + (
        list(VALIDITY_COLUMNS) if base.get("history") == "scd2" else []
    )


def base(
    spark: SparkSession, spec: dict, name: str, quarantined: bool = False
) -> DataFrame:
    """Base entity (or its quarantine): Landing grain, spec columns, platform columns."""
    entity = spec["base_entities"][name]
    df = landing_rows(spark, spec, name, quarantined)
    if "scd_valid_from_timestamp" in df.columns and entity.get("history") != "scd2":
        raise ValueError(f"{name}: Landing is SCD2, so the spec must set history: scd2")
    platform = [
        c
        for c in ("source_name", "source_file_name", "ingested_timestamp")
        if c in df.columns
    ]
    columns = ns.base_output_columns(entity)
    df = df.select(
        *columns, *_key_columns(entity)[len(entity["natural_key"]) :], *platform
    )
    for key in entity["natural_key"]:
        df = df.withMetadata(key, NATURAL_KEY_COMMENT)
    return _stamped(df)


def bridge(spark: SparkSession, spec: dict, name: str) -> DataFrame:
    """Bridge entity: parent key and validity plus one row per element."""
    entity = spec["bridge_entities"][name]
    parent = spec["base_entities"][entity["parent"]]
    df = landing_rows(spark, spec, entity["parent"])
    element = bridge_attribute(name, entity)
    if "explode" in entity:
        column, split = entity["explode"]["column"], entity["explode"]["split"]
        values = F.split(F.col(column), re.escape(split))
    else:
        pattern = ns.like_to_regex(entity["unpivot"]["columns_like"])
        keep = entity["unpivot"]["keep_when"]
        flags = [c for c in df.columns if pattern.fullmatch(c)]
        values = F.array(
            *[F.when(F.col(c).cast("string") == keep, F.lit(c)) for c in flags]
        )
    keys = _key_columns(parent)
    df = df.select(*keys, F.explode(values).alias(element), "ingested_timestamp").where(
        F.col(element).isNotNull()
    )
    for key in parent["natural_key"]:
        df = df.withMetadata(key, NATURAL_KEY_COMMENT)
    return _stamped(df)


def _member_values(
    spark: SparkSession, spec: dict, name: str
) -> list[tuple[str, DataFrame]]:
    """Per member of an extracted entity: (Landing table, non-null rows).

    Base members read the same Landing rows as their base entity (attribute
    columns exist only there); bridge members read the bridge's rows. Rows
    carry `value`, `source_column`, `ingested_timestamp`, and the
    parent value and attributes when the entity has them.
    """
    entity = spec["extracted_entities"][name]
    parent, attributes = entity.get("parent"), entity.get("attributes", [])
    result = []
    for kind, owner, column in ns.members(spec)[name]:
        if kind == "base":
            base_entity = spec["base_entities"][owner]
            extra = (
                [F.col(parent_column(base_entity, parent)).alias(parent)]
                if parent
                else []
            )
            df = landing_rows(spark, spec, owner).select(
                F.col(column).alias("value"),
                F.lit(column).alias("source_column"),
                *extra,
                *attributes,
                "ingested_timestamp",
            )
            table = landing_table(base_entity["from"])
        else:
            bridge_entity = spec["bridge_entities"][owner]
            source_column = (
                F.lit(bridge_entity["explode"]["column"])
                if "explode" in bridge_entity
                else F.col(column)
            )
            df = bridge(spark, spec, owner).select(
                F.col(column).alias("value"),
                source_column.alias("source_column"),
                "ingested_timestamp",
            )
            table = landing_table(bridge_entity["from"])
        result.append((table, df.where(F.col("value").isNotNull())))
    return result


def extracted(spark: SparkSession, spec: dict, name: str) -> DataFrame:
    """Extracted entity: one row per distinct value (+ parent and attributes)."""
    entity = spec["extracted_entities"][name]
    group = (
        ["value"]
        + ([entity["parent"]] if entity.get("parent") else [])
        + entity.get("attributes", [])
    )
    frames = [df.drop("source_column") for _, df in _member_values(spark, spec, name)]
    df = (
        reduce(DataFrame.unionByName, frames)
        .groupBy(*group)
        .agg(
            F.count("*").alias("row_count"),
            F.max("ingested_timestamp").alias("ingested_timestamp"),
        )
        .withColumn(
            "rdm_proposed_match_key", match_key_udf(F.col("value").cast("string"))
        )
        .withColumnRenamed("value", name)
        .select(
            name,
            *group[1:],
            "rdm_proposed_match_key",
            "row_count",
            "ingested_timestamp",
        )
        .withMetadata(name, NATURAL_KEY_COMMENT)
    )
    return _stamped(df)


def value_lineage(spark: SparkSession, spec: dict) -> DataFrame:
    """Where every extracted value was seen, with a row count per location (N9)."""
    frames = []
    for name in spec["extracted_entities"]:
        for table, df in _member_values(spark, spec, name):
            frames.append(
                df.select(
                    F.lit(name).alias("entity"),
                    F.col("value").cast("string").alias("value"),
                    F.lit(table).alias("source_table"),
                    "source_column",
                    "ingested_timestamp",
                )
            )
    df = (
        reduce(DataFrame.unionByName, frames)
        .groupBy("entity", "value", "source_table", "source_column")
        .agg(
            F.count("*").alias("row_count"),
            F.max("ingested_timestamp").alias("ingested_timestamp"),
        )
    )
    return _stamped(df)
