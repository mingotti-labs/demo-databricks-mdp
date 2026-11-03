# Append-only raw table for the ABS CPI: Auto Loader reads the dated JSON Lines files
# src/common/fetch_abs.py writes into bronze_abs.s3_raw and appends every new file.
# Every fetch is kept, so a full refresh replays the volume without calling the ABS.
# Values and periods stay text as the ABS sent them; ingested_timestamp is the fetch
# time the notebook wrote into the file, not the time this pipeline read it.
# Expectations warn only: bronze keeps what the ABS sent.
from pyspark import pipelines as dp
from pyspark.sql.functions import col

VOLUME = spark.conf.get("abs_volume_root")
COLUMNS = [
    "series_key",
    "time_period",
    "value",
    "measure",
    "index",
    "adjustment_type",
    "region",
    "frequency",
    "unit",
    "base_period",
    "obs_status",
    "ingested_timestamp",
]


@dp.table(cluster_by_auto=True)
@dp.expect_all(
    {
        "series_key_present": "series_key IS NOT NULL",
        "time_period_present": "time_period IS NOT NULL",
        "value_present": "value IS NOT NULL",
    }
)
def observations_raw():
    schema = ", ".join(f"`{c}` STRING" for c in COLUMNS)
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(schema)
        .load(f"{VOLUME}/observations/landing")
        .withColumn("ingested_timestamp", col("ingested_timestamp").cast("timestamp"))
        .withColumn("source_file_path", col("_metadata.file_path"))
    )
