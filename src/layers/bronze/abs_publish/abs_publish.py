# Bronze Publish for the ABS CPI by streaming Auto CDC from the append-only raw table,
# sequenced by the fetch time. SCD1 by series and period: the latest value wins, and
# raw keeps every earlier fetch, so a restated value (an index rebase) is never lost.
from pyspark import pipelines as dp

dp.create_streaming_table(
    name="bronze_abs_publish.observations_scd1",
    table_properties={"delta.enableChangeDataFeed": "true"},
    cluster_by_auto=True,
)
dp.create_auto_cdc_flow(
    target="bronze_abs_publish.observations_scd1",
    source="bronze_abs.observations_raw",
    keys=["series_key", "time_period"],
    sequence_by="ingested_timestamp",
    stored_as_scd_type=1,
)
