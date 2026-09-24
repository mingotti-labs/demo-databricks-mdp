# SCD Type 2 modeling of AirROI's market summary data -- SCD2 only, no
# SCD1 (a deliberate scope decision: SCD1 would just duplicate SCD2's
# `WHERE __END_AT IS NULL` filter for "current value").
#
# Keyed by the flat _country/_region/_locality columns market_summary_raw
# carries, not the API's own nested `market` map -- Auto CDC's `keys=`
# needs flat columns, not a struct/map type.
from pyspark import pipelines as dp

dp.create_streaming_table(name="market_summary_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="market_summary_scd2",
    source="bronze_airroi.market_summary_raw",
    keys=["_country", "_region", "_locality"],
    stored_as_scd_type=2,
)
