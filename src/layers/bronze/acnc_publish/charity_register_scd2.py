# SCD Type 2 modeling of the ACNC Charity Register -- see charity_register_scd1.py
# for why `source` points at the private charity_register_valid view.
#
# ingested_timestamp/transformed_timestamp (phase4e retrofit) are excluded
# from history tracking -- current_timestamp() differs on every run, so
# without this exclusion Auto CDC would version every row on every refresh
# regardless of whether the real data changed (same reasoning as AirROI's
# market_summary_scd2.py, the reference implementation for this pattern).
from pyspark import pipelines as dp

# pipelines.reset.allowed=false: a full refresh of the bronze pipeline is
# refused instead of truncating the history (openspec acnc-two-pipelines D6).
dp.create_streaming_table(
    name="bronze_acnc_publish.charity_register_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableRowTracking": "true",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_acnc_publish.charity_register_scd2",
    source="charity_register_valid",
    keys=["ABN"],
    stored_as_scd_type=2,
    track_history_except_column_list=["ingested_timestamp", "transformed_timestamp"],
)
