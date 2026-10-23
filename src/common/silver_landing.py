# Shared Silver Landing transform: SCD column rename + is_current (SCD2
# only), provenance columns, and natural-key-leading column order -- the
# mechanical conventions references/docs/medallion/silver.md defines once for every
# source, applied here instead of duplicating them per entity file.
from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def land(df: DataFrame, natural_keys: list[str], source_name: str, scd2: bool) -> DataFrame:
    if scd2:
        df = (
            df.withColumnRenamed("__START_AT", "scd_valid_from_timestamp")
            .withColumnRenamed("__END_AT", "scd_valid_to_timestamp")
            .withColumn("is_current", F.col("scd_valid_to_timestamp").isNull())
        )
    df = (
        df.withColumn("source_name", F.lit(source_name))
        .withColumn("source_file_name", F.lit(None).cast("string"))
        .withColumn("transformed_timestamp", F.current_timestamp())
    )
    ordered_columns = natural_keys + [c for c in df.columns if c not in natural_keys]
    df = df.select(*ordered_columns)
    for key in natural_keys:
        df = df.withMetadata(key, {"comment": "Natural key"})
    return df


def land_changes(
    spark, table: str, natural_keys: list[str], source_name: str, scd2: bool = True
) -> DataFrame:
    """Stream the rows Auto CDC inserted, updated or closed in `table`.

    Reads the table's change feed, so `land()`'s run-time stamp lands only on
    changed rows. For an SCD2 table `ingested_timestamp` is the version's
    `__START_AT`: the table carries no platform timestamps (openspec
    correct-platform-timestamps). An SCD1 table has no versions, so Landing
    keeps its columns as they are.
    """
    df = (
        spark.readStream.option("readChangeFeed", "true")
        .table(table)
        .where("_change_type IN ('insert', 'update_postimage')")
        .drop("_change_type", "_commit_timestamp")
    )
    if scd2:
        df = df.withColumn("ingested_timestamp", F.col("__START_AT"))
    return land(df, natural_keys=natural_keys, source_name=source_name, scd2=scd2)
