# SCD Type 1 modeling of the ABS CPI from the append-only raw table. Each run fetches
# the whole history, so the snapshot is the latest file: one current row per series and
# period, and a restated value (an index rebase) replaces the old one. Raw keeps every
# earlier fetch, so nothing is lost. A run whose values did not change writes nothing.
#
# The fetch time changes on every row at every run, so it is left out of the snapshot
# (with the other platform columns); otherwise every row would be rewritten each run.
# Change data feed on, for Silver Landing.
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
    name="bronze_abs_publish.observations_scd1",
    table_properties={"delta.enableChangeDataFeed": "true"},
    cluster_by_auto=True,
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_abs_publish.observations_scd1",
    source="observations_snapshot",
    keys=["series_key", "time_period"],
    stored_as_scd_type=1,
)
