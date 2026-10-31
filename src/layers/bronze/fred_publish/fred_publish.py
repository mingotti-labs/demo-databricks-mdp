# Bronze Publish for FRED by streaming Auto CDC from the append-only raw table,
# sequenced by the fetch time. Each file holds only the recent days of each series,
# so there is no full snapshot to compare. SCD1 by series and date: the latest value
# wins, and raw keeps every earlier fetch, so a revision is never lost.
from pyspark import pipelines as dp

dp.create_streaming_table(
    name="bronze_fred_publish.observations_scd1",
    table_properties={"delta.enableChangeDataFeed": "true"},
    cluster_by_auto=True,
)
dp.create_auto_cdc_flow(
    target="bronze_fred_publish.observations_scd1",
    source="bronze_fred.observations_raw",
    keys=["series_id", "observation_date"],
    sequence_by="ingested_timestamp",
    stored_as_scd_type=1,
)
