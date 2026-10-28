# Append-only raw tables for SEC: Auto Loader reads the dated JSON Lines files
# src/common/fetch_sec.py writes into bronze_sec.s3_raw and appends every new
# file. Every fetch is kept, so a full refresh replays the volume without
# calling SEC. Values stay text as SEC sent them; ingested_timestamp is the
# fetch time the task wrote into the file (one value per file), not the time
# this pipeline read it. Expectations warn only: bronze keeps what SEC sent.
from pyspark import pipelines as dp
from pyspark.sql.functions import col

VOLUME = spark.conf.get("sec_volume_root")
CIK_FORMAT = "cik RLIKE '^[0-9]{10}$'"


def read_landing(data_source: str, columns: list[str]):
    schema = ", ".join(f"{c} STRING" for c in columns + ["ingested_timestamp"])
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(schema)
        .load(f"{VOLUME}/{data_source}/landing")
        .withColumn("ingested_timestamp", col("ingested_timestamp").cast("timestamp"))
        .withColumn("source_file_path", col("_metadata.file_path"))
    )


@dp.table()
@dp.expect_all({"cik_format": CIK_FORMAT, "ticker_present": "ticker IS NOT NULL"})
def company_tickers_raw():
    return read_landing("company_tickers", ["cik", "ticker", "title"])


@dp.table(cluster_by_auto=True)
@dp.expect_all(
    {
        "cik_format": CIK_FORMAT,
        "concept_present": "concept IS NOT NULL",
        "unit_present": "unit IS NOT NULL",
        "end_present": "`end` IS NOT NULL",
        "val_present": "val IS NOT NULL",
        "accn_present": "accn IS NOT NULL",
    }
)
def company_facts_raw():
    return read_landing(
        "company_facts",
        [
            "cik",
            "entity_name",
            "taxonomy",
            "concept",
            "unit",
            "start",
            "end",
            "val",
            "accn",
            "fy",
            "fp",
            "form",
            "filed",
            "frame",
            "content_sha256",
        ],
    )
