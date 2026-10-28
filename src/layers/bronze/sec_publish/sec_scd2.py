# SCD Type 2 modeling of SEC's ticker list and company facts from the
# append-only raw tables. Each snapshot is the latest file: the latest fetch for
# tickers, each company's latest file for facts (a company is written only when
# its facts change, so its latest file is its current state). A company that
# leaves the index keeps its last facts as current; silver joins to membership.
#
# Bronze full pattern: platform columns are left out of the snapshot; Auto CDC
# versions each snapshot with the pipeline update's time (__START_AT, __END_AT)
# and Silver Landing reads the change feed. Facts key confirmed unique by probe
# P7 (start is empty on point-in-time values).
from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql.functions import col, max

PLATFORM_COLUMNS = ["ingested_timestamp", "content_sha256", "source_file_path", "_rescued_data"]
FACTS_KEYS = ["cik", "taxonomy", "concept", "unit", "accn", "start", "end"]


def latest(table: str, per: list[str]):
    """Rows of the latest file per group (the latest fetch overall when `per` is empty)."""
    window = Window.partitionBy(*per)
    return (
        spark.read.table(table)
        .withColumn("_latest", max("ingested_timestamp").over(window))
        .where(col("ingested_timestamp") == col("_latest"))
        .drop("_latest", *PLATFORM_COLUMNS)
    )


@dp.temporary_view()
def company_tickers_snapshot():
    return latest("bronze_sec.company_tickers_raw", [])


@dp.temporary_view()
def company_facts_snapshot():
    return latest("bronze_sec.company_facts_raw", ["cik"])


SCD2_PROPERTIES = {"pipelines.reset.allowed": "false", "delta.enableChangeDataFeed": "true"}

dp.create_streaming_table(
    name="bronze_sec_publish.company_tickers_scd2", table_properties=SCD2_PROPERTIES
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_sec_publish.company_tickers_scd2",
    source="company_tickers_snapshot",
    keys=["cik", "ticker"],
    stored_as_scd_type=2,
)

dp.create_streaming_table(
    name="bronze_sec_publish.company_facts_scd2",
    table_properties=SCD2_PROPERTIES,
    cluster_by_auto=True,
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_sec_publish.company_facts_scd2",
    source="company_facts_snapshot",
    keys=FACTS_KEYS,
    stored_as_scd_type=2,
)
