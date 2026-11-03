# SCD Type 2 modeling of the ABS CPI from the append-only raw table. Each run fetches
# the whole history, so the snapshot is the latest file; a restated value (an index
# rebase) closes the old version and opens a new one, and an unchanged value writes
# nothing.
#
# Bronze full pattern: platform columns are left out of the snapshot (the fetch time
# changes on every row at every run); Auto CDC versions each snapshot with the
# pipeline update's time (__START_AT, __END_AT) and Silver Landing reads the change
# feed.
from pyspark import pipelines as dp
from pyspark.sql.functions import col, max

PLATFORM_COLUMNS = ["ingested_timestamp", "source_file_path", "_rescued_data"]


@dp.temporary_view()
def observations_snapshot():
    """Rows of the latest fetch."""
    raw = spark.read.table("bronze_abs.observations_raw")
    latest = raw.agg(max("ingested_timestamp")).first()[0]
    return raw.where(col("ingested_timestamp") == latest).drop(*PLATFORM_COLUMNS)


dp.create_streaming_table(
    name="bronze_abs_publish.observations_scd2",
    table_properties={"pipelines.reset.allowed": "false", "delta.enableChangeDataFeed": "true"},
    cluster_by_auto=True,
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_abs_publish.observations_scd2",
    source="observations_snapshot",
    keys=["series_key", "time_period"],
    stored_as_scd_type=2,
)
