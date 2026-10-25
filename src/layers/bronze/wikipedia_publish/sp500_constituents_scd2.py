# SCD Type 2 modeling of the S&P 500 list: each version is a period a company
# was in the index, so a close is an exit and a new version is a join (the
# membership history, from the first load). Keyed by symbol (distinct over the
# real page: 503 rows, 503 symbols).
#
# Bronze full pattern (openspec rollout-bronze-full-pattern): raw stamps
# ingested_timestamp on every row at every load, so it is left out of the
# snapshot; Auto CDC versions each snapshot with the pipeline update's time
# (__START_AT, __END_AT) and Silver Landing reads the change feed.
from pyspark import pipelines as dp


@dp.temporary_view()
def sp500_constituents_snapshot():
    return spark.read.table("bronze_wikipedia.sp500_constituents_raw").drop("ingested_timestamp")


dp.create_streaming_table(
    name="bronze_wikipedia_publish.sp500_constituents_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_wikipedia_publish.sp500_constituents_scd2",
    source="sp500_constituents_snapshot",
    keys=["symbol"],
    stored_as_scd_type=2,
)
