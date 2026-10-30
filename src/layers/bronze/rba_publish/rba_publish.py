# Bronze Publish for the RBA by streaming Auto CDC from the append-only raw table,
# sequenced by the fetch time. Each file holds only the recent days of a table, so
# there is no full snapshot to compare. SCD1 by series and date: the latest value
# wins, and raw keeps every earlier fetch, so a revision is never lost.
from pyspark import pipelines as dp

dp.create_streaming_table(
    name="bronze_rba_publish.observations_scd1",
    table_properties={"delta.enableChangeDataFeed": "true"},
    cluster_by_auto=True,
)
dp.create_auto_cdc_flow(
    target="bronze_rba_publish.observations_scd1",
    source="bronze_rba.observations_raw",
    keys=["series_id", "observation_date"],
    sequence_by="ingested_timestamp",
    stored_as_scd_type=1,
)
