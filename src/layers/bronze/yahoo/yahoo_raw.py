# Append-only raw tables for Yahoo: Auto Loader reads the dated JSON Lines files
# src/common/fetch_yahoo.py writes into bronze_yahoo.s3_raw and appends every new
# file. Every fetch is kept, so a full refresh replays the volume without calling
# Yahoo. Values stay text as Yahoo sent them; ingested_timestamp is the fetch time
# the notebook wrote into the file, not the time this pipeline read it.
# Expectations warn only: bronze keeps what Yahoo sent.
from pyspark import pipelines as dp
from pyspark.sql.functions import col

VOLUME = spark.conf.get("yahoo_volume_root")
SYMBOL = ["symbol", "yahoo_symbol"]


def read_landing(dataset: str, columns: list[str]):
    schema = ", ".join(f"{c} STRING" for c in SYMBOL + columns + ["ingested_timestamp"])
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(schema)
        .load(f"{VOLUME}/{dataset}/landing")
        .withColumn("ingested_timestamp", col("ingested_timestamp").cast("timestamp"))
        .withColumn("source_file_path", col("_metadata.file_path"))
    )


@dp.table(cluster_by_auto=True)
@dp.expect_all(
    {
        "symbol_present": "symbol IS NOT NULL",
        "date_present": "date IS NOT NULL",
        "close_present": "close IS NOT NULL",
    }
)
def prices_raw():
    return read_landing("prices", ["date", "open", "high", "low", "close", "adj_close", "volume"])


@dp.table()
@dp.expect_all(
    {
        "symbol_present": "symbol IS NOT NULL",
        "date_present": "date IS NOT NULL",
        "event_type_known": "event_type IN ('dividend', 'split')",
        "value_present": "value IS NOT NULL",
    }
)
def events_raw():
    return read_landing("events", ["date", "event_type", "value"])


@dp.table()
@dp.expect("symbol_present", "symbol IS NOT NULL")
def calendar_raw():
    return read_landing("calendar", ["ex_dividend_date", "dividend_date", "earnings_date"])


@dp.table()
@dp.expect("symbol_present", "symbol IS NOT NULL")
def options_raw():
    return read_landing(
        "options",
        ["has_options", "expiry_count", "nearest_monthly_expiry", "open_interest", "volume"],
    )
