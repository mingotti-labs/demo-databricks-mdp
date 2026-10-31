# Append-only raw table for FRED: Auto Loader reads the dated JSON Lines files
# src/common/fetch_fred.py writes into bronze_fred.s3_raw and appends every new
# file. Every fetch is kept, so a full refresh replays the volume without calling
# FRED. Values, dates included, stay text as FRED sent them; ingested_timestamp is
# the fetch time the notebook wrote into the file, not the time this pipeline read
# it. Expectations warn only: bronze keeps what FRED sent.
from pyspark import pipelines as dp
from pyspark.sql.functions import col

VOLUME = spark.conf.get("fred_volume_root")
COLUMNS = [
    "series_id",
    "observation_date",
    "value",
    "title",
    "units",
    "frequency",
    "ingested_timestamp",
]


@dp.table(cluster_by_auto=True)
@dp.expect_all(
    {
        "series_id_present": "series_id IS NOT NULL",
        "observation_date_present": "observation_date IS NOT NULL",
        "value_present": "value IS NOT NULL",
    }
)
def observations_raw():
    schema = ", ".join(f"{c} STRING" for c in COLUMNS)
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(schema)
        .load(f"{VOLUME}/observations/landing")
        .withColumn("ingested_timestamp", col("ingested_timestamp").cast("timestamp"))
        .withColumn("source_file_path", col("_metadata.file_path"))
    )
