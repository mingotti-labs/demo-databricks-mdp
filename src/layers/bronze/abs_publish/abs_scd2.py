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
from pyspark.sql import Window
from pyspark.sql.functions import col, max

PLATFORM_COLUMNS = ["ingested_timestamp", "source_file_path", "_rescued_data"]


@dp.temporary_view()
def observations_snapshot():
    """Rows of the latest fetch, found with a window so it is evaluated at run time.

    An action such as `.first()` here would run while the pipeline graph is built,
    before this update has loaded raw: on a new environment raw is empty then and
    the snapshot would be empty.
    """
    latest = max("ingested_timestamp").over(Window.partitionBy())
    return (
        spark.read.table("bronze_abs.observations_raw")
        .withColumn("_latest", latest)
        .where(col("ingested_timestamp") == col("_latest"))
        .drop("_latest", *PLATFORM_COLUMNS)
    )


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
