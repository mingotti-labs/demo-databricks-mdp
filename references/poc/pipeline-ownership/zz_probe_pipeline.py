# Scratch pipeline for the ownership probe: the dividend story's shape in small.
# An Auto Loader raw table, an SCD1 Auto CDC target and a materialized view, in
# mdp_dev.bronze_yahoo, reading /Volumes/mdp_dev/bronze_yahoo/s3_raw/zz_probe/landing.
from pyspark import pipelines as dp
from pyspark.sql.functions import col

LANDING = "/Volumes/mdp_dev/bronze_yahoo/s3_raw/zz_probe/landing"


@dp.table(name="bronze_yahoo.zz_probe_raw")
def zz_probe_raw():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .schema("id STRING, value STRING, ingested_timestamp STRING")
        .load(LANDING)
        .withColumn("ingested_timestamp", col("ingested_timestamp").cast("timestamp"))
        .withColumn("source_file_path", col("_metadata.file_path"))
    )


dp.create_streaming_table(name="bronze_yahoo.zz_probe_scd1")
dp.create_auto_cdc_flow(
    target="bronze_yahoo.zz_probe_scd1",
    source="bronze_yahoo.zz_probe_raw",
    keys=["id"],
    sequence_by="ingested_timestamp",
    stored_as_scd_type=1,
)


@dp.materialized_view(name="bronze_yahoo.zz_probe_mv")
def zz_probe_mv():
    return spark.read.table("bronze_yahoo.zz_probe_raw").groupBy("id").count()
