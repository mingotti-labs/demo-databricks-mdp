# Append-only raw table for the RBA: Auto Loader reads the dated JSON Lines files
# src/common/fetch_rba.py writes into bronze_rba.s3_raw and appends every new
# file. Every fetch is kept, so a full refresh replays the volume without calling
# the RBA. Values, dates included, stay text as the RBA wrote them;
# ingested_timestamp is the fetch time the notebook wrote into the file, not the
# time this pipeline read it. Expectations warn only: bronze keeps what the RBA sent.
from pyspark import pipelines as dp
from pyspark.sql.functions import col

VOLUME = spark.conf.get("rba_volume_root")
COLUMNS = [
    "table_id",
    "series_id",
    "observation_date",
    "value",
    "title",
    "description",
    "frequency",
    "type",
    "units",
    "source",
    "publication_date",
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
